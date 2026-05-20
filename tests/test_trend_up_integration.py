# tests/test_trend_up_integration.py
"""端到端测试：验证 TREND_UP 状态下完整的止盈流程。"""
import pytest

from backend.core.context import MarketContext, IndicatorSnapshot
from backend.core.enums import ExitReason, MarketState
from backend.risk.portfolio import PortfolioPosition
from backend.signals.sell_signal import check_sell_signal


def test_trend_up_full_take_profit_flow():
    """TREND_UP 状态下完整止盈流程：TP1(40%) -> TP2(30%) -> 追踪(30%)。"""
    # portfolio：初始持仓 100g，均价 1000 元/克
    portfolio = PortfolioPosition()
    portfolio.buy(1000.0, 100.0)

    # ctx：构造 TREND_UP 市场上下文，并提供 2H/5分钟 EMA20
    ctx = MarketContext()
    ctx.market_state = MarketState.TREND_UP
    ctx.indicators = IndicatorSnapshot()
    ctx.indicators.ema_2h_20 = 1000.0
    ctx.indicators.ema_5m_20 = 1000.0

    # 阶段1：价格涨至 1016.07，触发 TP1，卖出当前持仓 40%
    ctx.price = 1016.07
    signal = check_sell_signal(portfolio, ctx)
    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_1
    assert signal.sell_ratio == pytest.approx(0.40)
    portfolio.sell(ctx.price, 100.0 * 0.40)
    portfolio.tp1_done = True

    # 阶段2：价格涨至 1024.10，触发 TP2，卖出初始仓位 30%，即剩余持仓 50%
    ctx.price = 1024.10
    signal = check_sell_signal(portfolio, ctx)
    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_2
    assert signal.sell_ratio == pytest.approx(0.50)
    portfolio.sell(ctx.price, 60.0 * 0.50)
    portfolio.tp2_done = True

    # 阶段3：价格回落跌破 2H EMA20，触发追踪止盈并清空剩余仓位
    ctx.price = 1015.0
    ctx.indicators.ema_2h_20 = 1018.0
    signal = check_sell_signal(portfolio, ctx)
    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_TRAILING
    assert signal.sell_ratio == pytest.approx(1.0)
    assert "2小时EMA20" in signal.reason
    portfolio.sell(ctx.price, 30.0)

    assert portfolio.is_empty()
