# backend/signals/sell_signal.py
from dataclasses import dataclass
from typing import Optional
from backend.core.enums import ExitReason
from backend.risk.portfolio import PortfolioPosition
from backend import config


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

    # 第2次止盈：tp1已执行且盈利≥1.2%，卖出初始仓位的20%
    # TP1已卖60%，剩余40%，要卖初始的20%需要卖剩余的50% (20%/40%=0.5)
    if portfolio.tp1_done and not portfolio.tp2_done and pnl >= config.TAKE_PROFIT_2_PCT:
        actual_sell_ratio = config.TAKE_PROFIT_2_SELL_RATIO / (1 - config.TAKE_PROFIT_1_SELL_RATIO)
        return SellSignalV2(
            exit_reason=ExitReason.TAKE_PROFIT_2,
            sell_ratio=actual_sell_ratio,
            reason=f"T仓整体盈利{pnl:.2%}≥{config.TAKE_PROFIT_2_PCT:.2%}，卖出初始仓位的20%",
        )

    # 第3次止盈（追踪）：tp1和tp2均已执行，金价跌破5分钟EMA20，清空剩余20%
    if portfolio.tp1_done and portfolio.tp2_done and price < ema20:
        return SellSignalV2(
            exit_reason=ExitReason.TAKE_PROFIT_TRAILING,
            sell_ratio=1.0,
            reason=f"金价{price:.2f}跌破5分钟EMA20={ema20:.2f}，清空剩余持仓",
        )

    return None
