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


# ── V2 组合止盈信号 ────────────────────────────────────────

from typing import Optional
from backend.core.enums import ExitReason
from backend.risk.position import PortfolioPosition


@dataclass
class SellSignalV2:
    exit_reason: ExitReason     # 触发原因（枚举）
    sell_ratio: float           # 相对当前持仓的卖出比例（0~1）
    reason: str                 # 人类可读说明


def check_sell_signal(
    portfolio: PortfolioPosition,
    ctx,
) -> Optional[SellSignalV2]:
    """
    检查是否触发组合止盈信号（V2）。

    优先级：tp1 > tp2 > 追踪止盈（EMA跌破）

    Args:
        portfolio: 当前 T仓组合持仓
        ctx: MarketContext（或 duck-type 兼容对象），需提供
             ctx.price 和 ctx.indicators.ema_5m_20

    Returns:
        SellSignalV2 实例，或 None（无信号）
    """
    if portfolio.is_empty():
        return None

    price: float = ctx.price
    ema20: float = ctx.indicators.ema_5m_20
    pnl: float = portfolio.pnl_pct(price)

    # 第1次止盈：盈利≥0.6%，卖出60%
    if not portfolio.tp1_done and pnl >= config.TAKE_PROFIT_1_PCT:
        return SellSignalV2(
            exit_reason=ExitReason.TAKE_PROFIT_1,
            sell_ratio=config.TAKE_PROFIT_1_SELL_RATIO,
            reason=f"T仓整体盈利{pnl:.2%}≥{config.TAKE_PROFIT_1_PCT:.2%}，卖出60%",
        )

    # 第2次止盈：tp1已执行且盈利≥1.2%，卖出20%
    if portfolio.tp1_done and not portfolio.tp2_done and pnl >= config.TAKE_PROFIT_2_PCT:
        return SellSignalV2(
            exit_reason=ExitReason.TAKE_PROFIT_2,
            sell_ratio=config.TAKE_PROFIT_2_SELL_RATIO,
            reason=f"T仓整体盈利{pnl:.2%}≥{config.TAKE_PROFIT_2_PCT:.2%}，卖出20%",
        )

    # 第3次止盈（追踪）：tp1已执行且金价跌破5分钟EMA20，清空剩余
    if portfolio.tp1_done and price < ema20:
        return SellSignalV2(
            exit_reason=ExitReason.TAKE_PROFIT_TRAILING,
            sell_ratio=1.0,
            reason=f"金价{price:.2f}跌破5分钟EMA20={ema20:.2f}，清空剩余持仓",
        )

    return None
