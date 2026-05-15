# backend/signals/exit_signal.py
from dataclasses import dataclass
from backend.core.context import MarketContext
from backend.core.enums import MarketState
from backend import config


@dataclass
class ExitSignal:
    triggered: bool
    reason: str


def check_exit(ctx: MarketContext, open_price: float, peak_price: float) -> ExitSignal:
    price = ctx.price
    ind = ctx.indicators
    pnl_rate = (price - open_price) / open_price

    # ATR动态止损
    if ind.atr_5m > 0:
        stop_price = open_price - config.OSC_STOP_LOSS_ATR_MULT * ind.atr_5m
        if price <= stop_price:
            return ExitSignal(True, f"ATR动态止损 price={price:.2f} stop={stop_price:.2f}")

    # 固定兜底止损
    if pnl_rate <= -config.SINGLE_STOP_LOSS_RATE:
        return ExitSignal(True, f"固定止损 pnl={pnl_rate:.3%}")

    # 隔夜保护止损（从最高价回撤0.8%）
    if peak_price > 0:
        overnight_drawdown = (peak_price - price) / peak_price
        if overnight_drawdown >= config.OVERNIGHT_TRAIL_RATE and pnl_rate > 0:
            return ExitSignal(True, f"隔夜保护止损 drawdown={overnight_drawdown:.3%}")

    # 下跌趋势中强制平仓
    if ctx.market_state == MarketState.TREND_DOWN:
        return ExitSignal(True, "趋势转跌强制平仓")

    return ExitSignal(False, "")
