# backend/signals/sell_signal.py
from dataclasses import dataclass
from backend.core.context import MarketContext
from backend.core.enums import MarketState
from backend import config


@dataclass
class SellSignal:
    triggered: bool
    reason: str


def check_sell(ctx: MarketContext, open_price: float, peak_price: float) -> SellSignal:
    price = ctx.price
    ind = ctx.indicators
    state = ctx.market_state
    pnl_rate = (price - open_price) / open_price

    if state in (MarketState.OSCILLATION, MarketState.TREND_DECAY):
        # 震荡：达到0.6%止盈目标
        if pnl_rate >= config.OSC_TAKE_PROFIT_RATE:
            return SellSignal(True, f"震荡止盈 pnl={pnl_rate:.3%}")
        # 震荡：触及布林上轨且盈利>=0.4%
        if ind.bb_upper > 0 and price >= ind.bb_upper and pnl_rate >= config.SELL_FEE_RATE:
            return SellSignal(True, f"布林上轨止盈 pnl={pnl_rate:.3%}")
        # 趋势衰减：回撤0.5%止盈
        if state == MarketState.TREND_DECAY and pnl_rate > 0:
            drawdown = (peak_price - price) / peak_price
            if drawdown >= config.TREND_DECAY_TRAIL:
                return SellSignal(True, f"趋势衰减回撤止盈 drawdown={drawdown:.3%}")

    elif state == MarketState.TREND_UP:
        # 趋势：跌破5分钟EMA20且盈利>=0.8%
        if (ind.ema_5m_20 > 0
                and price < ind.ema_5m_20
                and pnl_rate >= config.TREND_MIN_PROFIT):
            return SellSignal(True, f"趋势EMA跌破止盈 pnl={pnl_rate:.3%}")

    return SellSignal(False, "")
