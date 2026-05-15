import pytest
from unittest.mock import MagicMock
from backend.signals.buy_signal import check_buy_signal
from backend.risk.position import PortfolioPosition
from backend.core.enums import MarketState, SignalType
from backend.config import LOT1_AMOUNT_G, LOT2_AMOUNT_G, LOT3_AMOUNT_G


def make_context(price, bb_lower, atr_5m, market_state=MarketState.OSCILLATION,
                 rsi=35.0, ema_4h_20=1000.0, ema_4h_60=990.0):
    """构造模拟 MarketContext，使用 ctx.indicators.* 访问指标"""
    ctx = MagicMock()
    ctx.price = price
    ctx.market_state = market_state
    ctx.indicators = MagicMock()
    ctx.indicators.bb_lower = bb_lower
    ctx.indicators.atr_5m = atr_5m
    ctx.indicators.rsi = rsi
    ctx.indicators.ema_4h_20 = ema_4h_20
    ctx.indicators.ema_4h_60 = ema_4h_60
    return ctx


def empty_pos():
    """返回空仓 PortfolioPosition"""
    return PortfolioPosition(round_id=1)


# ── 震荡模式初始建仓 ──────────────────────────────────────

def test_initial_lot_triggers_on_bb_lower():
    """价格触及布林下轨时触发第1批建仓"""
    ctx = make_context(price=1000.0, bb_lower=1001.0, atr_5m=5.0)
    pos = empty_pos()
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False)
    assert signal is not None
    assert signal.signal_type == SignalType.BUY
    assert signal.amount_g == LOT1_AMOUNT_G


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
    pos = PortfolioPosition(round_id=1)
    pos.add_lot(1, 1000.0, LOT1_AMOUNT_G, 1000)
    ctx = make_context(price=994.0, bb_lower=1001.0, atr_5m=5.0)
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False,
                              last_buy_price=1000.0)
    assert signal is not None
    assert signal.signal_type == SignalType.ADD_LOT
    assert signal.amount_g == LOT2_AMOUNT_G


def test_add_lot3_triggers_after_another_atr_drop():
    """持仓80g，价格从上次买入再跌1×ATR(min=5)触发第3批加仓"""
    pos = PortfolioPosition(round_id=1)
    pos.add_lot(1, 1000.0, LOT1_AMOUNT_G, 1000)
    pos.add_lot(2, 993.0, LOT2_AMOUNT_G, 2000)
    # atr_5m=3 → max(3,5)=5，触发价=993-5=988，浮亏-1.34%未超-1.5%
    ctx = make_context(price=988.0, bb_lower=1001.0, atr_5m=3.0)
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False,
                              last_buy_price=993.0)
    assert signal is not None
    assert signal.signal_type == SignalType.ADD_LOT
    assert signal.amount_g == LOT3_AMOUNT_G


def test_no_add_lot_when_full():
    """满仓（100g）时不加仓"""
    pos = PortfolioPosition(round_id=1)
    pos.add_lot(1, 1000.0, LOT1_AMOUNT_G, 1000)
    pos.add_lot(2, 990.0, LOT2_AMOUNT_G, 2000)
    pos.add_lot(3, 980.0, LOT3_AMOUNT_G, 3000)
    ctx = make_context(price=970.0, bb_lower=1001.0, atr_5m=5.0)
    signal = check_buy_signal(ctx, pos, circuit_breaker_active=False,
                              last_buy_price=980.0)
    assert signal is None


def test_no_add_lot_when_loss_too_deep():
    """浮亏超过 STOP_ADD_LOSS_PCT（-1.5%）时停止加仓"""
    pos = PortfolioPosition(round_id=1)
    pos.add_lot(1, 1000.0, LOT1_AMOUNT_G, 1000)
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
