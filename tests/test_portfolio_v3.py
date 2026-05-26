import pytest

from backend.risk.portfolio import (
    PortfolioPosition,
    get_current_round_signals,
    load_portfolio_from_signals,
)


def insert_signal(conn, ts, sig_type, price, amount_g, pnl_yuan=None):
    """插入测试信号到 signals 表"""
    conn.execute(
        "INSERT INTO signals (ts, type, mode, price, amount_g, reason, pnl_yuan) "
        "VALUES (?, ?, 'OSCILLATION', ?, ?, 'test', ?)",
        (ts, sig_type, price, amount_g, pnl_yuan),
    )


def test_current_round_starts_after_last_full_clear(tmp_path):
    """验证当前轮次只包含最近一次全清仓之后的信号。"""
    from backend.db.database import init_db, get_conn
    import backend.db.database as db_mod

    db_mod.DB_PATH = tmp_path / "test.db"
    init_db()
    with get_conn() as conn:
        insert_signal(conn, 1000, "BUY", 1000.0, 50.0)
        insert_signal(conn, 2000, "STOP_LOSS_CLEAR", 980.0, 50.0, -120.0)
        insert_signal(conn, 3000, "BUY", 996.0, 50.0)
        conn.commit()
        rows = get_current_round_signals(conn)
    assert [row["ts"] for row in rows] == [3000]


def test_load_portfolio_rebuilds_amount_cost_flags_and_pnl(tmp_path):
    """验证从 signals 可以恢复当前 T 仓状态。"""
    from backend.db.database import init_db, get_conn
    import backend.db.database as db_mod

    db_mod.DB_PATH = tmp_path / "test.db"
    init_db()
    with get_conn() as conn:
        insert_signal(conn, 1000, "BUY", 1000.0, 50.0)
        insert_signal(conn, 2000, "ADD_LOT", 990.0, 30.0)
        insert_signal(conn, 3000, "TAKE_PROFIT_1", 1010.0, 48.0, 600.0)
        conn.commit()
        portfolio = load_portfolio_from_signals(conn)

    assert portfolio.total_amount_g == pytest.approx(32.0)
    assert portfolio.realized_pnl == pytest.approx(600.0)
    assert portfolio.tp1_done is True
    assert portfolio.tp2_done is False
    assert portfolio.last_buy_price is None


def test_load_portfolio_resets_buy_anchor_after_partial_sell_above_lot1(tmp_path):
    """验证重启回放时，部分止盈后剩余持仓大于50g会使用均价作为加仓锚点。"""
    from backend.db.database import init_db, get_conn
    import backend.db.database as db_mod

    db_mod.DB_PATH = tmp_path / "test.db"
    init_db()
    with get_conn() as conn:
        insert_signal(conn, 1000, "BUY", 1000.0, 50.0)
        insert_signal(conn, 2000, "ADD_LOT", 990.0, 30.0)
        insert_signal(conn, 3000, "ADD_LOT", 980.0, 20.0)
        insert_signal(conn, 4000, "TAKE_PROFIT_1", 1010.0, 40.0, 500.0)
        conn.commit()
        portfolio = load_portfolio_from_signals(conn)

    assert portfolio.total_amount_g == pytest.approx(60.0)
    assert portfolio.last_buy_price == pytest.approx(portfolio.avg_cost)
