# tests/test_signals.py
import pytest
from unittest.mock import MagicMock
from backend.core.context import MarketContext
from backend.core.enums import MarketState
from backend.core.context import IndicatorSnapshot
from backend.signals.regime_signal import detect_regime
from backend.signals.buy_signal import check_buy
from backend.signals.sell_signal import check_sell
from backend.signals.exit_signal import check_exit
import pandas as pd


def make_ctx(state=MarketState.OSCILLATION, price=1000.0, adx=18.0,
             plus_di=22.0, minus_di=18.0, bb_lower=995.0, bb_upper=1010.0,
             rsi=38.0, atr=3.0, ema_4h_20=1005.0, ema_4h_60=990.0,
             ema_5m_20=1002.0):
    adx_series = pd.Series([adx - 3, adx - 2, adx - 1, adx])
    ind = IndicatorSnapshot(
        adx=adx, plus_di=plus_di, minus_di=minus_di,
        adx_series=adx_series,
        bb_upper=bb_upper, bb_mid=1002.0, bb_lower=bb_lower,
        rsi=rsi, atr_5m=atr, ema_4h_20=ema_4h_20, ema_4h_60=ema_4h_60,
        ema_5m_20=ema_5m_20,
    )
    ctx = MarketContext(price=price, market_state=state, indicators=ind)
    return ctx


def test_regime_oscillation():
    ctx = make_ctx(adx=18.0)
    assert detect_regime(ctx) == MarketState.OSCILLATION


def test_regime_trend_up():
    ctx = make_ctx(adx=30.0, plus_di=28.0, minus_di=15.0)
    # ADX rising: series ends at 30, prev is 27
    ctx.indicators.adx_series = pd.Series([20, 24, 27, 30])
    assert detect_regime(ctx) == MarketState.TREND_UP


def test_regime_decay():
    ctx = make_ctx(adx=30.0, plus_di=28.0, minus_di=15.0)
    ctx.indicators.adx_series = pd.Series([35, 33, 31, 30])  # 下降
    assert detect_regime(ctx) == MarketState.TREND_DECAY


def test_buy_signal_oscillation_bb_lower():
    ctx = make_ctx(state=MarketState.OSCILLATION, price=994.0, bb_lower=995.0)
    sig = check_buy(ctx, open_positions=0, unit_g=20.0)
    assert sig.triggered


def test_buy_signal_no_trigger_above_lower():
    ctx = make_ctx(state=MarketState.OSCILLATION, price=1000.0, bb_lower=995.0)
    sig = check_buy(ctx, open_positions=0, unit_g=20.0)
    assert not sig.triggered


def test_buy_signal_max_positions():
    ctx = make_ctx(state=MarketState.OSCILLATION, price=994.0, bb_lower=995.0)
    sig = check_buy(ctx, open_positions=5, unit_g=20.0)
    assert not sig.triggered


def test_sell_signal_osc_take_profit():
    ctx = make_ctx(state=MarketState.OSCILLATION, price=1007.0)
    sig = check_sell(ctx, open_price=1000.0, peak_price=1007.0)
    assert sig.triggered


def test_sell_signal_no_trigger_below_target():
    ctx = make_ctx(state=MarketState.OSCILLATION, price=1003.0)
    sig = check_sell(ctx, open_price=1000.0, peak_price=1003.0)
    assert not sig.triggered


def test_exit_signal_atr_stop():
    ctx = make_ctx(price=993.0, atr=3.0)
    sig = check_exit(ctx, open_price=1000.0, peak_price=1000.0)
    assert sig.triggered  # stop = 1000 - 2*3 = 994


def test_exit_signal_fixed_stop():
    ctx = make_ctx(price=984.0, atr=0.0)
    sig = check_exit(ctx, open_price=1000.0, peak_price=1000.0)
    assert sig.triggered  # -1.6% > -1.5%


def test_exit_no_trigger():
    ctx = make_ctx(price=1002.0, atr=3.0)
    sig = check_exit(ctx, open_price=1000.0, peak_price=1002.0)
    assert not sig.triggered
