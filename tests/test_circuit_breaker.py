# tests/test_circuit_breaker.py
import pytest
import time
from datetime import datetime
from backend.db.database import init_db
from backend.db.database import get_conn
from backend.risk.circuit_breaker import CircuitBreaker
from backend import config


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    import backend.db.database as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    init_db()


def test_no_trigger_normal_tick():
    cb = CircuitBreaker()
    cb.check_tick(price=1000.0, prev_price=999.0, price_5m_ago=999.5)
    assert not cb.is_active


def test_level1_tick_trigger():
    cb = CircuitBreaker()
    cb.check_tick(price=1006.0, prev_price=1000.0, price_5m_ago=1000.0)
    assert cb.is_active
    assert cb.state.level == 1


def test_level1_5min_trigger():
    cb = CircuitBreaker()
    cb.check_tick(price=1016.0, prev_price=1015.9, price_5m_ago=1000.0)
    assert cb.is_active
    assert cb.state.level == 1


def test_level2_atr_trigger():
    cb = CircuitBreaker()
    cb.check_atr(atr_current=9.0, atr_daily_mean=3.0)
    assert cb.is_active
    assert cb.state.level == 2


def test_level2_pauses_for_24_hours(monkeypatch):
    """验证二级熔断触发后暂停24小时。"""
    import backend.risk.circuit_breaker as cb_mod

    now_seconds = 1_700_000_000
    monkeypatch.setattr(cb_mod.time, "time", lambda: now_seconds)
    cb = CircuitBreaker()

    cb.check_atr(atr_current=9.0, atr_daily_mean=3.0)

    assert cb.state.resume_ts == now_seconds * 1000 + config.CB_LONG_PAUSE_HOURS * 60 * 60_000


def test_level3_daily_stop():
    cb = CircuitBreaker()
    cb.on_stop_loss()
    cb.on_stop_loss()
    assert not cb.is_active
    cb.on_stop_loss()
    assert cb.is_active
    assert cb.state.level == 3


def test_level3_stop_count_resets_after_cst_date_changes(monkeypatch):
    """验证进程跨北京时间自然日运行时，三级熔断止损计数会重新开始。"""
    import backend.risk.circuit_breaker as cb_mod

    first_day_seconds = datetime.fromisoformat("2026-06-09T12:00:00+08:00").timestamp()
    second_day_seconds = datetime.fromisoformat("2026-06-10T12:00:00+08:00").timestamp()
    monkeypatch.setattr(cb_mod.time, "time", lambda: first_day_seconds)
    cb = CircuitBreaker()

    cb.on_stop_loss()
    cb.on_stop_loss()
    assert not cb.is_active

    monkeypatch.setattr(cb_mod.time, "time", lambda: second_day_seconds)
    cb.on_stop_loss()

    assert not cb.is_active
    assert cb._daily_stop_count == 1


def test_level3_pauses_for_24_hours(monkeypatch):
    """验证三级熔断触发后暂停24小时。"""
    import backend.risk.circuit_breaker as cb_mod

    now_seconds = 1_700_000_000
    monkeypatch.setattr(cb_mod.time, "time", lambda: now_seconds)
    cb = CircuitBreaker()

    for _ in range(config.CB3_DAILY_STOP_COUNT):
        cb.on_stop_loss()

    assert cb.state.resume_ts == now_seconds * 1000 + config.CB_LONG_PAUSE_HOURS * 60 * 60_000


def test_level3_manual_resume():
    cb = CircuitBreaker()
    cb.on_stop_loss()
    cb.on_stop_loss()
    cb.on_stop_loss()
    assert cb.is_active
    cb.manual_resume()
    assert not cb.is_active


def test_no_double_trigger_when_active():
    cb = CircuitBreaker()
    cb.check_tick(price=1006.0, prev_price=1000.0, price_5m_ago=1000.0)
    level = cb.state.level
    cb.check_atr(atr_current=9.0, atr_daily_mean=3.0)
    assert cb.state.level == level  # 不被覆盖


def test_restore_daily_stop_count_from_today_signals(monkeypatch):
    """验证后端重启时会从当天止损信号恢复三级熔断计数。"""
    import backend.risk.circuit_breaker as cb_mod

    now_seconds = 1_700_000_000
    today_stop_ts = now_seconds * 1000 - 60_000
    old_stop_ts = now_seconds * 1000 - 25 * 60 * 60_000
    monkeypatch.setattr(cb_mod.time, "time", lambda: now_seconds)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO signals (ts, type, mode, price, amount_g, reason, pnl_yuan) "
            "VALUES (?, 'STOP_LOSS_CLEAR', 'OSCILLATION', 970.0, 50.0, 'test', -100.0)",
            (today_stop_ts,),
        )
        conn.execute(
            "INSERT INTO signals (ts, type, mode, price, amount_g, reason, pnl_yuan) "
            "VALUES (?, 'STOP_LOSS_HALF', 'OSCILLATION', 980.0, 25.0, 'test', -50.0)",
            (old_stop_ts,),
        )
        conn.commit()

    cb = CircuitBreaker()

    assert cb._daily_stop_count == 1


def test_restore_active_breaker_state_from_logs(monkeypatch):
    """验证后端重启时会恢复尚未到期的熔断状态。"""
    import backend.risk.circuit_breaker as cb_mod

    now_seconds = 1_700_000_000
    resume_ts = now_seconds * 1000 + 60_000
    monkeypatch.setattr(cb_mod.time, "time", lambda: now_seconds)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO circuit_breaker_logs (trigger_ts, level, reason, trigger_value, resume_ts) "
            "VALUES (?, 2, 'ATR异常', 3.0, ?)",
            (now_seconds * 1000 - 60_000, resume_ts),
        )
        conn.commit()

    cb = CircuitBreaker()

    assert cb.is_active
    assert cb.state.level == 2
    assert cb.state.reason == "ATR异常"
    assert cb.state.resume_ts == resume_ts


def test_ignore_expired_breaker_state_from_logs(monkeypatch):
    """验证后端重启时不会恢复已经到期的熔断状态。"""
    import backend.risk.circuit_breaker as cb_mod

    now_seconds = 1_700_000_000
    monkeypatch.setattr(cb_mod.time, "time", lambda: now_seconds)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO circuit_breaker_logs (trigger_ts, level, reason, trigger_value, resume_ts) "
            "VALUES (?, 2, 'ATR异常', 3.0, ?)",
            (now_seconds * 1000 - 120_000, now_seconds * 1000 - 60_000),
        )
        conn.commit()

    cb = CircuitBreaker()

    assert not cb.is_active
