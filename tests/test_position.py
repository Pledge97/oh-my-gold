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
