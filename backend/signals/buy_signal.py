# backend/signals/buy_signal.py
from dataclasses import dataclass
from backend.core.context import MarketContext
from backend.core.enums import MarketState
from backend import config


@dataclass
class BuySignal:
    triggered: bool
    amount_g: float
    reason: str


def check_buy(ctx: MarketContext, open_positions: int, unit_g: float) -> BuySignal:
    no_signal = BuySignal(False, 0.0, "")

    if open_positions >= 5:
        return no_signal

    ind = ctx.indicators
    price = ctx.price
    state = ctx.market_state

    if state in (MarketState.OSCILLATION, MarketState.TREND_DECAY):
        # 震荡模式：价格触及布林下轨
        if ind.bb_lower > 0 and price <= ind.bb_lower:
            return BuySignal(True, unit_g, f"布林下轨触及 price={price:.2f} lower={ind.bb_lower:.2f}")

    elif state == MarketState.TREND_UP:
        # 趋势模式：4H EMA20>EMA60 且 RSI回调至超卖
        if (ind.ema_4h_20 > ind.ema_4h_60
                and ind.rsi <= config.TREND_RSI_OVERSOLD):
            return BuySignal(True, unit_g, f"趋势回调买入 RSI={ind.rsi:.1f}")

    return no_signal
