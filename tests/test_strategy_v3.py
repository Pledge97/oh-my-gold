"""
tests/test_strategy_v3.py
验证 V3 引擎：只写 signals，不写 positions/position_lots。
"""
import pytest

from backend.core.enums import MarketState
from backend.db.database import init_db, get_conn
from backend.risk.portfolio import PortfolioPosition
from backend.strategy.engine import StrategyEngine


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """每个测试使用独立的临时数据库，避免测试间状态污染。"""
    import backend.db.database as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    init_db()


def test_save_sell_signal_persists_pnl_yuan():
    """验证卖出信号会写入本次实现盈亏。"""
    engine = StrategyEngine()
    with get_conn() as conn:
        engine._save_signal_raw(
            conn=conn,
            ts=1000,
            sig_type="TAKE_PROFIT_1",
            mode=MarketState.OSCILLATION.value,
            price=1010.0,
            amount_g=50.0,
            reason="test",
            pnl_yuan=298.0,
        )
        row = conn.execute("SELECT pnl_yuan FROM signals WHERE type='TAKE_PROFIT_1'").fetchone()
    assert row["pnl_yuan"] == pytest.approx(298.0)


def test_portfolio_snapshot_has_no_lots_field():
    """验证 WebSocket portfolio 不再返回 lots 字段。"""
    engine = StrategyEngine()
    engine._portfolio = PortfolioPosition(round_counter=3)
    engine._portfolio.buy(1000.0, 50.0)
    ctx = type("Ctx", (), {"indicators": type("I", (), {"atr_5m": 5.0, "bb_lower": 990.0})()})()
    snapshot = engine._portfolio_snapshot(1010.0, engine._portfolio.pnl_pct(1010.0), ctx)
    assert snapshot["round_counter"] == 3
    assert "lots" not in snapshot
