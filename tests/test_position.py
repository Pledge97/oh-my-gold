# tests/test_position.py
import pytest
from backend.db.database import init_db, get_conn
from backend.risk.position import PositionManager, Position
from backend.core.enums import CloseType


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    import backend.db.database as db_mod
    from pathlib import Path
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    init_db()


def test_open_position():
    pm = PositionManager()
    pos = pm.open(price=1000.0, amount_g=20.0)
    assert pos.id is not None
    assert pos.open_price == 1000.0
    assert pos.amount_g == 20.0
    assert pos.peak_price == 1000.0


def test_add_position_updates_avg():
    pm = PositionManager()
    pos = pm.open(price=1000.0, amount_g=20.0)
    pm.add(pos, price=990.0, amount_g=10.0)
    expected_avg = (1000.0 * 20 + 990.0 * 10) / 30
    assert abs(pos.open_price - expected_avg) < 0.01
    assert pos.amount_g == 30.0
    assert pos.add_count == 1


def test_close_position_pnl():
    pm = PositionManager()
    pos = pm.open(price=1000.0, amount_g=20.0)
    result = pm.close(pos, price=1010.0, close_type=CloseType.TAKE_PROFIT)
    fee = 1010.0 * 20.0 * 0.004
    expected_pnl = (1010.0 - 1000.0) * 20.0 - fee
    assert abs(result["pnl_yuan"] - expected_pnl) < 0.01


def test_load_open_positions():
    pm = PositionManager()
    pm.open(price=1000.0, amount_g=20.0)
    pm.open(price=995.0, amount_g=20.0)
    positions = pm.load_open()
    assert len(positions) == 2


# ── PortfolioPosition V2 测试 ──────────────────────────────
import pytest
from backend.risk.position import PortfolioPosition


def make_portfolio():
    return PortfolioPosition(round_id=1)


def test_portfolio_initial_state():
    pos = make_portfolio()
    assert pos.total_amount_g == 0.0
    assert pos.total_cost == 0.0
    assert pos.is_empty()


def test_portfolio_add_lot_increases_amount():
    pos = make_portfolio()
    pos.add_lot(lot_index=1, price=1000.0, amount_g=50.0, ts=1000)
    assert pos.total_amount_g == 50.0
    assert pos.total_cost == pytest.approx(50_000.0)


def test_portfolio_add_two_lots():
    pos = make_portfolio()
    pos.add_lot(1, 1000.0, 50.0, 1000)
    pos.add_lot(2, 990.0, 30.0, 2000)
    assert pos.total_amount_g == 80.0
    assert pos.total_cost == pytest.approx(50_000 + 29_700)


def test_portfolio_pnl_pct_profit():
    pos = make_portfolio()
    pos.add_lot(1, 1000.0, 50.0, 1000)
    # 扣除0.4%手续费后：(1010 * 0.996 - 1000) / 1000 = 0.5960%
    expected = (1010.0 * 0.996 - 1000.0) / 1000.0
    assert pos.pnl_pct(current_price=1010.0) == pytest.approx(expected)


def test_portfolio_pnl_pct_loss():
    pos = make_portfolio()
    pos.add_lot(1, 1000.0, 50.0, 1000)
    pos.add_lot(2, 990.0, 30.0, 2000)
    total_cost = 50 * 1000 + 30 * 990
    market_val = 80 * 950
    fee = market_val * 0.004
    expected = (market_val - fee - total_cost) / total_cost
    assert pos.pnl_pct(current_price=950.0) == pytest.approx(expected)


def test_portfolio_avg_cost():
    pos = make_portfolio()
    pos.add_lot(1, 1000.0, 50.0, 1000)
    pos.add_lot(2, 990.0, 30.0, 2000)
    assert pos.avg_cost == pytest.approx(79_700 / 80)


def test_portfolio_reduce_by_ratio():
    pos = make_portfolio()
    pos.add_lot(1, 1000.0, 50.0, 1000)
    pos.add_lot(2, 990.0, 30.0, 2000)
    sold_g = pos.reduce(ratio=0.60, close_price=1010.0, ts=3000)
    assert sold_g == pytest.approx(80 * 0.60)
    assert pos.total_amount_g == pytest.approx(80 * 0.40)


def test_portfolio_reduce_updates_cost():
    pos = make_portfolio()
    pos.add_lot(1, 1000.0, 100.0, 1000)
    pos.reduce(ratio=0.60, close_price=1010.0, ts=2000)
    assert pos.total_amount_g == pytest.approx(40.0)
    assert pos.total_cost == pytest.approx(40 * 1000.0)


def test_portfolio_clear_all():
    pos = make_portfolio()
    pos.add_lot(1, 1000.0, 50.0, 1000)
    pos.add_lot(2, 990.0, 30.0, 2000)
    sold_g = pos.clear(close_price=1005.0, ts=3000)
    assert sold_g == pytest.approx(80.0)
    assert pos.is_empty()


def test_portfolio_tp_flags():
    pos = make_portfolio()
    assert not pos.tp1_done
    assert not pos.tp2_done
    pos.add_lot(1, 1000.0, 50.0, 1000)
    pos.mark_tp1()
    assert pos.tp1_done
    pos.mark_tp2()
    assert pos.tp2_done
