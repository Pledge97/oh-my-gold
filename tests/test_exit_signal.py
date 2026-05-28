# tests/test_exit_signal.py
import pytest
from unittest.mock import MagicMock
from backend.signals.exit_signal import check_exit_signal, get_next_stop_price
from backend.risk.portfolio import PortfolioPosition
from backend.core.enums import MarketState, ExitReason


def make_portfolio(avg_cost, total_g):
    """创建持有 total_g 克、均价 avg_cost 的组合仓位（V3）"""
    pos = PortfolioPosition()
    pos.buy(avg_cost, total_g)
    return pos


def make_context(market_state=MarketState.OSCILLATION):
    ctx = MagicMock()
    ctx.market_state = market_state
    return ctx


def test_no_signal_when_empty():
    """空仓时无止损信号"""
    pos = PortfolioPosition()
    signal = check_exit_signal(pos, current_price=1000.0, ctx=make_context())
    assert signal is None


def test_no_signal_when_loss_below_threshold():
    """浮亏-2%，未到-2.5%阈值，无减仓信号"""
    pos = make_portfolio(1000.0, 80.0)
    signal = check_exit_signal(pos, current_price=980.0, ctx=make_context())
    assert signal is None


def test_no_signal_at_minus_1_5_pct():
    """浮亏-1.5%，仅停加仓（由buy_signal处理），exit_signal不返回信号"""
    pos = make_portfolio(1000.0, 50.0)
    signal = check_exit_signal(pos, current_price=985.0, ctx=make_context())
    assert signal is None


def test_force_half_at_minus_2_5_pct():
    """浮亏-2.5%时卖出50%持仓"""
    pos = make_portfolio(1000.0, 80.0)
    signal = check_exit_signal(pos, current_price=975.0, ctx=make_context())
    assert signal is not None
    assert signal.exit_reason == ExitReason.STOP_LOSS_HALF
    assert signal.sell_ratio == pytest.approx(0.50)


def test_no_repeat_half_after_stop_loss_half_done():
    """已执行减半止损后，价格仍在减半区间时不重复卖出50%。"""
    pos = make_portfolio(1000.0, 80.0)
    pos.stop_loss_half_done = True

    signal = check_exit_signal(pos, current_price=975.0, ctx=make_context())

    assert signal is None


def test_clear_all_still_works_after_stop_loss_half_done():
    """已执行减半止损后，跌到清仓线仍触发全部清仓。"""
    pos = make_portfolio(1000.0, 80.0)
    pos.stop_loss_half_done = True

    signal = check_exit_signal(pos, current_price=965.0, ctx=make_context())

    assert signal is not None
    assert signal.exit_reason == ExitReason.STOP_LOSS_CLEAR
    assert signal.sell_ratio == pytest.approx(1.0)


def test_next_stop_price_skips_half_after_stop_loss_half_done():
    """已执行减半止损后，下一止损价直接显示清仓触发价。"""
    pos = make_portfolio(1000.0, 80.0)
    pos.stop_loss_half_done = True

    next_stop = get_next_stop_price(pos, current_pnl_pct=-0.01)

    assert next_stop == pytest.approx(968.88, abs=0.01)


def test_clear_all_at_minus_3_5_pct():
    """浮亏-3.5%时全部清仓"""
    pos = make_portfolio(1000.0, 100.0)
    signal = check_exit_signal(pos, current_price=965.0, ctx=make_context())
    assert signal is not None
    assert signal.exit_reason == ExitReason.STOP_LOSS_CLEAR
    assert signal.sell_ratio == pytest.approx(1.0)


def test_clear_all_takes_priority_over_half():
    """浮亏-3.5%时触发清仓（不是减半）"""
    pos = make_portfolio(1000.0, 100.0)
    # 浮亏-4%，超过-3.5%阈值
    signal = check_exit_signal(pos, current_price=960.0, ctx=make_context())
    assert signal.exit_reason == ExitReason.STOP_LOSS_CLEAR


def test_trend_clear_on_trend_down():
    """趋势转空时立即清仓"""
    pos = make_portfolio(1000.0, 80.0)
    ctx = make_context(market_state=MarketState.TREND_DOWN)
    signal = check_exit_signal(pos, current_price=1005.0, ctx=ctx)
    assert signal is not None
    assert signal.exit_reason == ExitReason.TREND_CLEAR
    assert signal.sell_ratio == pytest.approx(1.0)


def test_trend_clear_takes_priority_over_loss():
    """趋势清仓优先级高于亏损清仓"""
    pos = make_portfolio(1000.0, 100.0)
    ctx = make_context(market_state=MarketState.TREND_DOWN)
    # 即使盈利也清仓
    signal = check_exit_signal(pos, current_price=1010.0, ctx=ctx)
    assert signal.exit_reason == ExitReason.TREND_CLEAR


def test_no_trend_clear_on_oscillation():
    """震荡模式不触发趋势清仓"""
    pos = make_portfolio(1000.0, 80.0)
    ctx = make_context(market_state=MarketState.OSCILLATION)
    signal = check_exit_signal(pos, current_price=1005.0, ctx=ctx)
    assert signal is None
