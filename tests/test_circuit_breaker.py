# tests/test_circuit_breaker.py
import pytest
import time
from backend.db.database import init_db
from backend.risk.circuit_breaker import CircuitBreaker


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


def test_level3_daily_stop():
    cb = CircuitBreaker()
    cb.on_stop_loss()
    cb.on_stop_loss()
    assert not cb.is_active
    cb.on_stop_loss()
    assert cb.is_active
    assert cb.state.level == 3


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
