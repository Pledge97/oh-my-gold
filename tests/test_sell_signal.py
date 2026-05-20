# tests/test_sell_signal.py
import pytest
from unittest.mock import MagicMock
from backend.signals.sell_signal import check_sell_signal
from backend.risk.portfolio import PortfolioPosition
from backend.core.enums import ExitReason, MarketState


def make_portfolio(avg_cost, total_g):
    """创建一个持有 total_g 克、均价 avg_cost 的组合仓位（V3）"""
    pos = PortfolioPosition()
    pos.buy(avg_cost, total_g)
    return pos


def make_context(price, ema_5m_20=None):
    """创建模拟市场上下文，ema_5m_20 默认为价格的 99%"""
    # ctx：卖出信号测试使用的最小市场上下文
    ctx = MagicMock()
    ctx.price = price
    ctx.market_state = None
    ctx.indicators = MagicMock()
    ctx.indicators.ema_5m_20 = ema_5m_20 if ema_5m_20 is not None else price * 0.99
    ctx.indicators.ema_2h_20 = 0.0
    return ctx


def test_no_signal_when_empty():
    """空仓时不触发任何信号"""
    pos = PortfolioPosition()
    signal = check_sell_signal(pos, make_context(1000.0))
    assert signal is None


def test_tp1_triggers_at_0_6_pct():
    """扣除0.4%手续费后净盈利达到0.6%时触发第1次止盈"""
    pos = make_portfolio(avg_cost=1000.0, total_g=50.0)
    # 触发价 = 1000 * 1.006 / 0.996 ≈ 1010.05
    ctx = make_context(price=1010.05, ema_5m_20=990.0)
    signal = check_sell_signal(pos, ctx)
    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_1
    assert signal.sell_ratio == pytest.approx(0.60)


def test_tp1_not_triggered_below_threshold():
    """盈利不足 0.6% 时不触发止盈"""
    pos = make_portfolio(avg_cost=1000.0, total_g=50.0)
    ctx = make_context(price=1005.0, ema_5m_20=990.0)
    signal = check_sell_signal(pos, ctx)
    assert signal is None


def test_tp1_only_fires_once():
    """tp1_done=True 后不重复触发第1次止盈"""
    pos = make_portfolio(avg_cost=1000.0, total_g=50.0)
    pos.tp1_done = True
    ctx = make_context(price=1010.0, ema_5m_20=990.0)
    signal = check_sell_signal(pos, ctx)
    assert signal is None or signal.exit_reason != ExitReason.TAKE_PROFIT_1


def test_tp2_triggers_at_1_2_pct():
    """扣除0.4%手续费后净盈利达到1.2%时触发第2次止盈，卖出初始仓位的20%（剩余的50%）"""
    pos = make_portfolio(avg_cost=1000.0, total_g=50.0)
    pos.tp1_done = True
    # 触发价 = 1000 * 1.012 / 0.996 ≈ 1016.07
    ctx = make_context(price=1016.07, ema_5m_20=990.0)
    signal = check_sell_signal(pos, ctx)
    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_2
    # TP1已卖60%，剩余40%，要卖初始的20%需要卖剩余的50% (0.2/0.4=0.5)
    assert signal.sell_ratio == pytest.approx(0.50)


def test_tp2_requires_tp1_done():
    """tp1 未执行时，即使盈利≥1.2% 也先触发 tp1"""
    pos = make_portfolio(avg_cost=1000.0, total_g=50.0)
    ctx = make_context(price=1015.0, ema_5m_20=990.0)
    signal = check_sell_signal(pos, ctx)
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_1


def test_trailing_tp_on_ema_break():
    """金价跌破5分钟EMA20，清空剩余持仓"""
    pos = make_portfolio(avg_cost=1000.0, total_g=20.0)
    pos.tp1_done = True
    pos.tp2_done = True
    ctx = make_context(price=998.0, ema_5m_20=1001.0)
    signal = check_sell_signal(pos, ctx)
    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_TRAILING
    assert signal.sell_ratio == pytest.approx(1.0)


def test_no_trailing_tp_when_price_above_ema():
    """金价高于EMA20时不触发追踪止盈"""
    pos = make_portfolio(avg_cost=1000.0, total_g=20.0)
    pos.tp1_done = True
    pos.tp2_done = True
    ctx = make_context(price=1005.0, ema_5m_20=1001.0)
    signal = check_sell_signal(pos, ctx)
    assert signal is None


def test_no_trailing_tp_without_tp1():
    """tp1 未执行时，即使价格跌破EMA也不触发追踪止盈"""
    pos = make_portfolio(avg_cost=1000.0, total_g=50.0)
    ctx = make_context(price=998.0, ema_5m_20=1001.0)
    signal = check_sell_signal(pos, ctx)
    assert signal is None or signal.exit_reason == ExitReason.TAKE_PROFIT_1


def test_no_trailing_tp_without_tp2():
    """tp1已执行但tp2未执行时，价格跌破EMA不触发追踪止盈"""
    pos = make_portfolio(avg_cost=1000.0, total_g=50.0)
    pos.tp1_done = True
    ctx = make_context(price=998.0, ema_5m_20=1001.0)
    signal = check_sell_signal(pos, ctx)
    assert signal is None or signal.exit_reason != ExitReason.TAKE_PROFIT_TRAILING


def test_trend_up_tp1_triggers_at_1_2_pct():
    """TREND_UP 状态下，扣除手续费后净盈利达到 1.2% 时触发第1次止盈。"""
    pos = make_portfolio(avg_cost=1000.0, total_g=50.0)
    # ctx：触发价 = 1000 * 1.012 / 0.996 ≈ 1016.07
    ctx = make_context(price=1016.07, ema_5m_20=990.0)
    ctx.market_state = MarketState.TREND_UP
    ctx.indicators.ema_2h_20 = 990.0

    signal = check_sell_signal(pos, ctx)

    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_1
    assert signal.sell_ratio == pytest.approx(0.40)


def test_trend_up_tp2_triggers_at_2_0_pct():
    """TREND_UP 状态下，盈利达到 2.0% 时触发第2次止盈。"""
    pos = make_portfolio(avg_cost=1000.0, total_g=50.0)
    pos.tp1_done = True
    # ctx：触发价 = 1000 * 1.020 / 0.996 ≈ 1024.10
    ctx = make_context(price=1024.10, ema_5m_20=990.0)
    ctx.market_state = MarketState.TREND_UP
    ctx.indicators.ema_2h_20 = 990.0

    signal = check_sell_signal(pos, ctx)

    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_2
    assert signal.sell_ratio == pytest.approx(0.50)


def test_trend_up_trailing_uses_2h_ema():
    """TREND_UP 状态下，追踪止盈使用 2H EMA20 而不是 5分钟 EMA20。"""
    pos = make_portfolio(avg_cost=1000.0, total_g=20.0)
    pos.tp1_done = True
    pos.tp2_done = True
    # ctx：价格跌破 2H EMA20，但仍高于 5分钟 EMA20
    ctx = make_context(price=1005.0, ema_5m_20=1001.0)
    ctx.market_state = MarketState.TREND_UP
    ctx.indicators.ema_2h_20 = 1008.0

    signal = check_sell_signal(pos, ctx)

    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_TRAILING
    assert "2小时EMA20" in signal.reason


def test_non_trend_up_uses_original_logic():
    """非 TREND_UP 状态下，继续使用原始止盈逻辑。"""
    pos = make_portfolio(avg_cost=1000.0, total_g=50.0)
    # ctx：触发价 = 1000 * 1.006 / 0.996 ≈ 1010.05
    ctx = make_context(price=1010.05, ema_5m_20=990.0)
    ctx.market_state = MarketState.OSCILLATION
    ctx.indicators.ema_2h_20 = 990.0

    signal = check_sell_signal(pos, ctx)

    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_1
    assert signal.sell_ratio == pytest.approx(0.60)
