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
