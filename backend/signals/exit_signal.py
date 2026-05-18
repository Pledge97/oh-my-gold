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


# ── V2 组合止损信号 ────────────────────────────────────────

from typing import Optional
from backend.core.enums import ExitReason
from backend.risk.portfolio import PortfolioPosition


@dataclass
class ExitSignalV2:
    exit_reason: ExitReason   # 触发原因枚举
    sell_ratio: float         # 卖出比例：0.0~1.0，相对当前持仓
    reason: str               # 人类可读的原因描述


def check_exit_signal(
    portfolio: PortfolioPosition,
    current_price: float,
    ctx,
) -> Optional[ExitSignalV2]:
    """
    检查是否触发组合止损/清仓信号（V2）。

    优先级：趋势清仓 > 亏损清仓(-3.5%) > 亏损减半(-2.5%)

    Args:
        portfolio: 当前组合持仓
        current_price: 当前市场价格（元/g）
        ctx: MarketContext，需包含 market_state 字段

    Returns:
        ExitSignalV2 若触发止损，否则 None
    """
    if portfolio.is_empty():
        return None

    # 优先级1：趋势转空，立即清仓
    if ctx.market_state == MarketState.TREND_DOWN:
        return ExitSignalV2(
            exit_reason=ExitReason.TREND_CLEAR,
            sell_ratio=1.0,
            reason="趋势转空（TREND_DOWN），立即清仓",
        )

    pnl = portfolio.pnl_pct(current_price)

    # 优先级2：亏损≥-3.5%，全部清仓
    if pnl <= config.CLEAR_ALL_LOSS_PCT:
        return ExitSignalV2(
            exit_reason=ExitReason.STOP_LOSS_CLEAR,
            sell_ratio=1.0,
            reason=f"T仓浮亏{pnl:.2%}≤{config.CLEAR_ALL_LOSS_PCT:.2%}，全部清仓",
        )

    # 优先级3：亏损≥-2.5%，强制减仓50%
    if pnl <= config.FORCE_HALF_LOSS_PCT:
        return ExitSignalV2(
            exit_reason=ExitReason.STOP_LOSS_HALF,
            sell_ratio=0.50,
            reason=f"T仓浮亏{pnl:.2%}≤{config.FORCE_HALF_LOSS_PCT:.2%}，强制减仓50%",
        )

    return None
