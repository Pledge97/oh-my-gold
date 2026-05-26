# tests/test_position.py
# ── PortfolioPosition V3 测试 ──────────────────────────────
import pytest
from backend.risk.portfolio import PortfolioPosition


def make_portfolio():
    """创建空的 V3 PortfolioPosition"""
    return PortfolioPosition()


def test_portfolio_initial_state():
    pos = make_portfolio()
    assert pos.total_amount_g == 0.0
    assert pos.total_cost == 0.0
    assert pos.is_empty()


def test_portfolio_add_lot_increases_amount():
    """测试买入增加持仓量"""
    pos = make_portfolio()
    pos.buy(price=1000.0, amount_g=50.0)
    assert pos.total_amount_g == 50.0
    assert pos.total_cost == pytest.approx(50_000.0)


def test_portfolio_add_two_lots():
    """测试两次买入累加持仓"""
    pos = make_portfolio()
    pos.buy(1000.0, 50.0)
    pos.buy(990.0, 30.0)
    assert pos.total_amount_g == 80.0
    assert pos.total_cost == pytest.approx(50_000 + 29_700)


def test_portfolio_pnl_pct_profit():
    """测试盈利时的盈亏率计算（扣除手续费）"""
    pos = make_portfolio()
    pos.buy(1000.0, 50.0)
    # 扣除0.4%手续费后：(1010 * 0.996 - 1000) / 1000 = 0.5960%
    expected = (1010.0 * 0.996 - 1000.0) / 1000.0
    assert pos.pnl_pct(current_price=1010.0) == pytest.approx(expected)


def test_portfolio_pnl_pct_loss():
    """测试亏损时的盈亏率计算"""
    pos = make_portfolio()
    pos.buy(1000.0, 50.0)
    pos.buy(990.0, 30.0)
    total_cost = 50 * 1000 + 30 * 990
    market_val = 80 * 950
    fee = market_val * 0.004
    expected = (market_val - fee - total_cost) / total_cost
    assert pos.pnl_pct(current_price=950.0) == pytest.approx(expected)


def test_portfolio_avg_cost():
    """测试加权平均成本计算"""
    pos = make_portfolio()
    pos.buy(1000.0, 50.0)
    pos.buy(990.0, 30.0)
    assert pos.avg_cost == pytest.approx(79_700 / 80)


def test_portfolio_reduce_by_ratio():
    """测试按比例卖出（V3 使用 sell 方法）"""
    pos = make_portfolio()
    pos.buy(1000.0, 50.0)
    pos.buy(990.0, 30.0)
    sold_g = 80 * 0.60
    pos.sell(price=1010.0, amount_g=sold_g)
    assert pos.total_amount_g == pytest.approx(80 * 0.40)


def test_portfolio_reduce_updates_cost():
    """测试卖出后成本更新"""
    pos = make_portfolio()
    pos.buy(1000.0, 100.0)
    pos.sell(price=1010.0, amount_g=60.0)
    assert pos.total_amount_g == pytest.approx(40.0)
    assert pos.total_cost == pytest.approx(40 * 1000.0)


def test_partial_sell_above_lot1_resets_last_buy_price_to_avg_cost():
    """卖出后剩余持仓大于首批仓位时，加仓锚点重置为剩余均价。"""
    pos = make_portfolio()
    pos.buy(1000.0, 50.0)
    pos.buy(990.0, 30.0)
    pos.buy(980.0, 20.0)
    avg_cost = pos.avg_cost
    pos.sell(price=1010.0, amount_g=40.0)
    assert pos.total_amount_g == pytest.approx(60.0)
    assert pos.last_buy_price == pytest.approx(avg_cost)


def test_clear_all_resets_last_buy_price():
    """清仓后清除最近买入价，避免下一轮误用上一轮锚点。"""
    pos = make_portfolio()
    pos.buy(1000.0, 50.0)
    pos.sell(price=1010.0, amount_g=50.0)
    assert pos.last_buy_price is None


def test_portfolio_clear_all():
    """测试全部清仓"""
    pos = make_portfolio()
    pos.buy(1000.0, 50.0)
    pos.buy(990.0, 30.0)
    pos.sell(price=1005.0, amount_g=80.0)
    assert pos.is_empty()


def test_portfolio_tp_flags():
    """测试止盈标志（V3 不再有 mark_tp1/mark_tp2 方法，直接设置属性）"""
    pos = make_portfolio()
    assert not pos.tp1_done
    assert not pos.tp2_done
    pos.buy(1000.0, 50.0)
    pos.tp1_done = True
    assert pos.tp1_done
    pos.tp2_done = True
    assert pos.tp2_done
