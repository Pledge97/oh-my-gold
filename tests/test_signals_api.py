import pytest

from backend.api.routes import get_signals
from backend.db.database import get_conn, init_db


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """每个用例使用独立测试库，避免污染本地开发数据。"""
    import backend.db.database as db_mod

    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    init_db()


def test_signals_include_circuit_breaker_logs():
    """验证信号接口会合并返回熔断日志。"""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO signals (ts, type, mode, price, amount_g, reason, pnl_yuan) "
            "VALUES (1000, 'BUY', 'OSCILLATION', 980.0, 50.0, 'test buy', NULL)"
        )
        conn.execute(
            "INSERT INTO circuit_breaker_logs (trigger_ts, level, reason, trigger_value, resume_ts) "
            "VALUES (2000, 2, 'ATR异常', 3.0, 3000)"
        )
        conn.commit()

    rows = get_signals(limit=10)

    assert rows[0]["id"] == "cb-1"
    assert rows[0]["ts"] == 2000
    assert rows[0]["type"] == "CIRCUIT_BREAKER_2"
    assert rows[0]["price"] is None
    assert rows[0]["amount_g"] is None
    assert rows[0]["pnl_yuan"] is None
    assert rows[0]["reason"] == "ATR异常"
    assert rows[1]["type"] == "BUY"
