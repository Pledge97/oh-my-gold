import pytest
from unittest.mock import MagicMock
from backend.signals.buy_signal import check_buy_signal, get_next_buy_price
from backend.risk.portfolio import PortfolioPosition
from backend.core.enums import ExitReason, MarketState, SignalType
from backend.config import LOT1_AMOUNT_G, LOT2_AMOUNT_G, LOT3_AMOUNT_G


def make_context(price, bb_lower, atr_5m, market_state=MarketState.OSCILLATION,
                 rsi=35.0, ema_4h_20=1000.0, ema_4h_60=990.0):
    """构造模拟 MarketContext，使用 ctx.indicators.* 访问指标"""
    ctx = MagicMock()
    ctx.price = price
    ctx.ts = 0
    ctx.market_state = market_state
    ctx.indicators = MagicMock()
    ctx.indicators.bb_lower = bb_lower
    ctx.indicators.atr_5m = atr_5m
    ctx.indicators.rsi = rsi
    ctx.indicators.ema_4h_20 = ema_4h_20
    ctx.indicators.ema_4h_60 = ema_4h_60
    return ctx


def empty_pos():
    """返回空仓 PortfolioPosition（V3 不需要 round_id）"""
    return PortfolioPosition()


# ── 震荡模式初始建仓 ──────────────────────────────────────

def test_initial_lot_triggers_on_bb_lower():
    """价格触及布林下轨时触发第1批建仓"""
    ctx = make_context(price=1000.0, bb_lower=1001.0, atr_5m=5.0)
    pos = empty_pos()
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False)
    assert signal is not None
    assert signal.signal_type == SignalType.BUY
    assert signal.amount_g == LOT1_AMOUNT_G


def test_initial_lot_does_not_trigger_when_price_only_touches_bb_lower():
    """价格只是贴近布林下轨时不触发第1批建仓。"""
    ctx = make_context(price=981.38, bb_lower=981.45, atr_5m=5.0)
    pos = empty_pos()

    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False)

    assert signal is None


def test_initial_lot_triggers_after_bb_lower_break_buffer():
    """价格跌破布林下轨缓冲后触发第1批建仓。"""
    ctx = make_context(price=980.45, bb_lower=981.45, atr_5m=5.0)
    pos = empty_pos()

    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False)

    assert signal is not None
    assert signal.signal_type == SignalType.BUY


def test_no_signal_price_above_bb_lower():
    """价格高于布林下轨时不触发"""
    ctx = make_context(price=1010.0, bb_lower=1000.0, atr_5m=5.0)
    pos = empty_pos()
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False)
    assert signal is None


def test_no_signal_when_circuit_breaker_active():
    """熔断激活时禁止建仓"""
    ctx = make_context(price=999.0, bb_lower=1001.0, atr_5m=5.0)
    pos = empty_pos()
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=True)
    assert signal is None


# ── 加仓（第2/3批）────────────────────────────────────────

def test_add_lot2_triggers_after_1atr_drop():
    """持仓50g，价格从上次买入跌1×ATR触发第2批加仓"""
    pos = PortfolioPosition()
    pos.buy(1000.0, LOT1_AMOUNT_G)
    ctx = make_context(price=994.0, bb_lower=1001.0, atr_5m=5.0)
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False,
                              last_buy_price=1000.0)
    assert signal is not None
    assert signal.signal_type == SignalType.ADD_LOT
    assert signal.amount_g == LOT2_AMOUNT_G


def test_full_clear_blocks_reentry_after_normal_cooldown():
    """清仓后，普通30分钟冷却结束仍不能重新建仓。"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 100.0)
    pos.sell(1010.0, 100.0, ts=60_000, exit_reason=ExitReason.TAKE_PROFIT_TRAILING.value)
    ctx = make_context(price=1009.0, bb_lower=1011.0, atr_5m=5.0)
    ctx.ts = 60_000 + 31 * 60 * 1000

    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False)

    assert signal is None


def test_full_clear_blocks_early_reentry_before_min_price_gap():
    """清仓冷却期内，价格只继续下跌3个ATR但未达到20元最小间距时不买回。"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 100.0)
    pos.sell(1010.0, 100.0, ts=60_000, exit_reason=ExitReason.TAKE_PROFIT_TRAILING.value)
    ctx = make_context(price=995.0, bb_lower=1011.0, atr_5m=5.0)
    ctx.ts = 120_000

    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False)

    assert signal is None


def test_full_clear_allows_early_reentry_after_strict_price_gap():
    """清仓冷却期内，价格继续下跌达到严格间距后允许提前买回。"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 100.0)
    pos.sell(1010.0, 100.0, ts=60_000, exit_reason=ExitReason.TAKE_PROFIT_TRAILING.value)
    ctx = make_context(price=990.0, bb_lower=1011.0, atr_5m=5.0)
    ctx.ts = 120_000

    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False)

    assert signal is not None
    assert signal.signal_type == SignalType.BUY


def test_full_clear_allows_reentry_after_strict_cooldown():
    """清仓12小时冷却结束后，满足建仓条件时允许重新买入。"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 100.0)
    pos.sell(1010.0, 100.0, ts=60_000, exit_reason=ExitReason.TAKE_PROFIT_TRAILING.value)
    ctx = make_context(price=1009.0, bb_lower=1011.0, atr_5m=5.0)
    ctx.ts = 60_000 + 12 * 60 * 60 * 1000

    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False)

    assert signal is not None
    assert signal.signal_type == SignalType.BUY


def test_add_lot3_triggers_after_another_atr_drop():
    """持仓80g，价格从上次买入再跌1×ATR(min=5)触发第3批加仓"""
    pos = PortfolioPosition()
    pos.buy(1000.0, LOT1_AMOUNT_G)
    pos.buy(993.0, LOT2_AMOUNT_G)
    # atr_5m=3 → max(3,5)=5，触发价=993-5=988，浮亏-1.34%未超-1.5%
    ctx = make_context(price=988.0, bb_lower=1001.0, atr_5m=3.0)
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False,
                              last_buy_price=993.0)
    assert signal is not None
    assert signal.signal_type == SignalType.ADD_LOT
    assert signal.amount_g == LOT3_AMOUNT_G


def test_no_add_lot_when_full():
    """满仓（100g）时不加仓"""
    pos = PortfolioPosition()
    pos.buy(1000.0, LOT1_AMOUNT_G)
    pos.buy(990.0, LOT2_AMOUNT_G)
    pos.buy(980.0, LOT3_AMOUNT_G)
    ctx = make_context(price=970.0, bb_lower=1001.0, atr_5m=5.0)
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False,
                              last_buy_price=980.0)
    assert signal is None


def test_no_add_lot_when_loss_too_deep():
    """浮亏超过 STOP_ADD_LOSS_PCT（-1.5%）时停止加仓"""
    pos = PortfolioPosition()
    pos.buy(1000.0, LOT1_AMOUNT_G)
    # 当前价985，浮亏-1.5%
    ctx = make_context(price=985.0, bb_lower=1001.0, atr_5m=5.0)
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False,
                              last_buy_price=1000.0)
    assert signal is None


# ── 趋势模式建仓 ─────────────────────────────────────────

def test_trend_buy_on_rsi_oversold():
    """趋势上涨模式，EMA20>EMA60 且 RSI超卖时初始建仓"""
    ctx = make_context(price=1000.0, bb_lower=900.0, atr_5m=5.0,
                       market_state=MarketState.TREND_UP,
                       rsi=38.0, ema_4h_20=1010.0, ema_4h_60=990.0)
    pos = empty_pos()
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False)
    assert signal is not None
    assert signal.amount_g == LOT1_AMOUNT_G


def test_trend_buy_requires_ema20_above_ema60():
    """趋势上涨模式，EMA20 <= EMA60 时不建仓"""
    ctx = make_context(price=1000.0, bb_lower=900.0, atr_5m=5.0,
                       market_state=MarketState.TREND_UP,
                       rsi=35.0, ema_4h_20=990.0, ema_4h_60=1010.0)
    pos = empty_pos()
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False)
    assert signal is None


def test_no_buy_on_trend_down():
    """趋势下跌模式禁止建仓"""
    ctx = make_context(price=999.0, bb_lower=1001.0, atr_5m=5.0,
                       market_state=MarketState.TREND_DOWN)
    pos = empty_pos()
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False)
    assert signal is None


def test_add_refills_partial_position_to_50g():
    """持仓低于50g时，加仓补到50g。"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 20.0)
    ctx = make_context(price=994.0, bb_lower=1001.0, atr_5m=5.0)
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False, last_buy_price=1000.0)
    assert signal is not None
    assert signal.amount_g == pytest.approx(30.0)


def test_partial_position_uses_bb_lower_not_last_buy_drop():
    """持仓低于50g时，按空仓布林下轨价格补回第一档。"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 20.0)
    ctx = make_context(price=994.0, bb_lower=990.0, atr_5m=5.0)
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False, last_buy_price=1000.0)
    assert signal is None


def test_next_buy_price_for_partial_position_below_lot1_uses_bb_lower():
    """持仓低于50g时，下一次买入展示价使用布林下轨缓冲价。"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 20.0)
    ctx = make_context(price=994.0, bb_lower=990.0, atr_5m=5.0)
    assert get_next_buy_price(pos, ctx) == pytest.approx(989.0)


def test_add_refills_50_to_80g():
    """持仓50g到80g之间时，加仓补到80g。"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 50.0)
    ctx = make_context(price=994.0, bb_lower=1001.0, atr_5m=5.0)
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False, last_buy_price=1000.0)
    assert signal is not None
    assert signal.amount_g == pytest.approx(30.0)


def test_add_refills_80_to_100g():
    """持仓80g到100g之间时，加仓补到100g。"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 80.0)
    ctx = make_context(price=994.0, bb_lower=1001.0, atr_5m=5.0)
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False, last_buy_price=1000.0)
    assert signal is not None
    assert signal.amount_g == pytest.approx(20.0)


def test_recent_take_profit_blocks_same_price_refill():
    """刚止盈后，即使命中布林下轨，也不按近似卖出价补回仓位。"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 100.0)
    pos.sell(1010.0, 60.0, ts=60_000, exit_reason=ExitReason.TAKE_PROFIT_1.value)
    ctx = make_context(price=1009.0, bb_lower=1011.0, atr_5m=5.0)
    ctx.ts = 120_000

    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False, last_buy_price=pos.last_buy_price)

    assert signal is None


def test_recent_sell_allows_refill_after_cooldown():
    """卖出冷却结束后，重新满足买入条件时允许补仓。"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 100.0)
    pos.sell(1010.0, 60.0, ts=60_000, exit_reason=ExitReason.TAKE_PROFIT_1.value)
    ctx = make_context(price=1009.0, bb_lower=1011.0, atr_5m=5.0)
    ctx.ts = 60_000 + 31 * 60 * 1000

    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False, last_buy_price=pos.last_buy_price)

    assert signal is not None
    assert signal.signal_type == SignalType.ADD_LOT


def test_recent_sell_blocks_refill_after_one_atr_drop():
    """冷却期内价格只跌1倍ATR时，仍阻止补仓。"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 100.0)
    pos.sell(1010.0, 60.0, ts=60_000, exit_reason=ExitReason.TAKE_PROFIT_1.value)
    ctx = make_context(price=1004.0, bb_lower=1011.0, atr_5m=5.0)
    ctx.ts = 120_000

    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False, last_buy_price=pos.last_buy_price)

    assert signal is None


def test_recent_sell_allows_refill_after_two_atr_drop():
    """冷却期内价格相对卖出价继续下跌2倍ATR后，允许提前补仓。"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 100.0)
    pos.sell(1010.0, 60.0, ts=60_000, exit_reason=ExitReason.TAKE_PROFIT_1.value)
    ctx = make_context(price=1000.0, bb_lower=1011.0, atr_5m=5.0)
    ctx.ts = 120_000

    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False, last_buy_price=pos.last_buy_price)

    assert signal is not None
    assert signal.signal_type == SignalType.ADD_LOT
