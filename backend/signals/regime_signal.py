# backend/signals/regime_signal.py
from backend.core.context import MarketContext
from backend.core.enums import MarketState
from backend import config


def detect_regime(ctx: MarketContext) -> MarketState:
    ind = ctx.indicators
    adx = ind.adx
    adx_series = ind.adx_series

    if adx_series is None or len(adx_series.dropna()) < config.ADX_LOOKBACK + 1:
        return MarketState.OSCILLATION

    adx_prev = float(adx_series.dropna().iloc[-(config.ADX_LOOKBACK + 1)])
    adx_rising = adx > adx_prev

    if adx < config.ADX_TREND_THRESHOLD:
        return MarketState.OSCILLATION

    if not adx_rising:
        return MarketState.TREND_DECAY

    if ind.plus_di > ind.minus_di:
        return MarketState.TREND_UP
    return MarketState.TREND_DOWN
