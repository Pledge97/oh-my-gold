import pytest
from fastapi.testclient import TestClient

from backend.db.database import init_db, get_conn
from backend.main import app


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    import backend.db.database as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    init_db()


def test_base_holdings_create_list_and_close():
    """验证底仓 API 可以创建、查询、平仓。"""
    client = TestClient(app)
    created = client.post(
        "/api/base_holdings",
        json={"amount_g": 10.0, "open_price": 990.0, "open_date": "2026-05-18"},
    )
    assert created.status_code == 200
    pos_id = created.json()["id"]

    listed = client.get("/api/base_holdings?status=OPEN")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    closed = client.post(
        f"/api/base_holdings/{pos_id}/close",
        json={"close_price": 1000.0, "close_date": "2026-05-18 10:30"},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"


def test_performance_uses_signals_and_base_holdings():
    """验证绩效统计来自 signals.pnl_yuan 和 base_holdings.pnl_yuan。"""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO signals (ts, type, mode, price, amount_g, reason, pnl_yuan) "
            "VALUES (1, 'TAKE_PROFIT_1', 'OSCILLATION', 1010, 50, 'test', 298)"
        )
        conn.execute(
            "INSERT INTO base_holdings (open_ts, open_price, amount_g, status, close_ts, close_price, pnl_yuan) "
            "VALUES (1, 990, 10, 'CLOSED', 2, 1000, 60)"
        )
        conn.commit()

    client = TestClient(app)
    data = client.get("/api/performance").json()
    assert data["total_trades"] == 1
    assert data["total_pnl_yuan"] == pytest.approx(298.0)
    assert data["cumulative_pnl_yuan"] == pytest.approx(358.0)
