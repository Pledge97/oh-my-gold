import pytest
from backend.risk.portfolio import PortfolioPosition
from backend import config


def test_full_since_ts_none_initially():
    """初始状态 full_since_ts 为 None"""
    pos = PortfolioPosition()
    assert pos.full_since_ts is None


def test_full_since_ts_set_when_full():
    """买入后达到满仓，full_since_ts 被记录"""
    pos = PortfolioPosition()
    pos.buy(1000.0, config.T_MAX_AMOUNT_G, ts=12345678)
    assert pos.full_since_ts == 12345678


def test_full_since_ts_not_set_when_partial():
    """买入后未达到满仓，full_since_ts 保持 None"""
    pos = PortfolioPosition()
    pos.buy(1000.0, config.LOT1_AMOUNT_G, ts=12345678)  # 50g，未满仓
    assert pos.full_since_ts is None


def test_full_since_ts_set_only_once():
    """多次加仓达到满仓，full_since_ts 只记录第一次满仓时间"""
    pos = PortfolioPosition()
    pos.buy(1000.0, config.LOT1_AMOUNT_G, ts=1000)   # 50g
    pos.buy(990.0, config.LOT2_AMOUNT_G, ts=2000)    # 80g
    pos.buy(980.0, config.LOT3_AMOUNT_G, ts=3000)    # 100g，满仓
    assert pos.full_since_ts == 3000


def test_full_since_ts_cleared_after_sell():
    """卖出后持仓低于满仓，full_since_ts 清除"""
    pos = PortfolioPosition()
    pos.buy(1000.0, config.T_MAX_AMOUNT_G, ts=1000)
    assert pos.full_since_ts == 1000
    pos.sell(1010.0, 10.0, ts=2000)  # 卖出 10g，剩余 90g < 100g
    assert pos.full_since_ts is None


def test_full_since_ts_not_cleared_when_still_full():
    """卖出后持仓仍等于满仓，full_since_ts 保持不变（理论上不会发生，防御性测试）"""
    pos = PortfolioPosition()
    pos.buy(1000.0, config.T_MAX_AMOUNT_G, ts=1000)
    # 卖出 0g（边界情况）
    pos.sell(1010.0, 0.0, ts=2000)
    assert pos.full_since_ts == 1000


def test_buy_without_ts_still_works():
    """不传 ts 时 buy() 正常工作，full_since_ts 保持 None（向后兼容）"""
    pos = PortfolioPosition()
    pos.buy(1000.0, config.T_MAX_AMOUNT_G)
    # 不传 ts，full_since_ts 不应被设置
    assert pos.full_since_ts is None


def test_sell_without_ts_still_works():
    """不传 ts 时 sell() 正常工作（向后兼容）"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 50.0)
    pos.sell(1010.0, 20.0)
    assert pos.total_amount_g == pytest.approx(30.0)


def test_full_since_ts_resets_after_sell_and_refill():
    """卖出降至未满仓后重新买入满仓，full_since_ts 重置为新的满仓时间"""
    pos = PortfolioPosition()
    pos.buy(1000.0, config.T_MAX_AMOUNT_G, ts=1000)  # 满仓，full_since_ts=1000
    pos.sell(1010.0, 10.0, ts=2000)                  # 降至 90g，full_since_ts 清除
    assert pos.full_since_ts is None
    pos.buy(1005.0, 10.0, ts=3000)                   # 重新满仓，full_since_ts=3000
    assert pos.full_since_ts == 3000


def test_load_portfolio_restores_full_since_ts():
    """重启恢复：满仓状态下，full_since_ts 从最后一笔买入信号的 ts 推导"""
    import sqlite3
    from backend.risk.portfolio import load_portfolio_from_signals
    from backend import config

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            type TEXT NOT NULL,
            mode TEXT,
            price REAL,
            amount_g REAL,
            reason TEXT,
            pnl_yuan REAL
        )
    """)
    # 模拟三批买入达到满仓
    conn.execute("INSERT INTO signals (ts, type, mode, price, amount_g, reason) VALUES (1000, 'BUY', 'OSCILLATION', 1000.0, 50.0, '')")
    conn.execute("INSERT INTO signals (ts, type, mode, price, amount_g, reason) VALUES (2000, 'ADD_LOT', 'OSCILLATION', 990.0, 30.0, '')")
    conn.execute("INSERT INTO signals (ts, type, mode, price, amount_g, reason) VALUES (3000, 'ADD_LOT', 'OSCILLATION', 980.0, 20.0, '')")
    conn.commit()

    portfolio = load_portfolio_from_signals(conn)

    assert portfolio.total_amount_g == pytest.approx(100.0)
    assert portfolio.full_since_ts == 3000  # 最后一笔买入的 ts


def test_load_portfolio_no_full_since_ts_when_not_full():
    """重启恢复：未满仓时，full_since_ts 为 None"""
    import sqlite3
    from backend.risk.portfolio import load_portfolio_from_signals

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            type TEXT NOT NULL,
            mode TEXT,
            price REAL,
            amount_g REAL,
            reason TEXT,
            pnl_yuan REAL
        )
    """)
    conn.execute("INSERT INTO signals (ts, type, mode, price, amount_g, reason) VALUES (1000, 'BUY', 'OSCILLATION', 1000.0, 50.0, '')")
    conn.commit()

    portfolio = load_portfolio_from_signals(conn)

    assert portfolio.total_amount_g == pytest.approx(50.0)
    assert portfolio.full_since_ts is None
