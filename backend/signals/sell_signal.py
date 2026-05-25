# backend/signals/sell_signal.py
from dataclasses import dataclass
from typing import Optional
from backend.core.enums import ExitReason, MarketState
from backend.risk.portfolio import PortfolioPosition
from backend import config
from backend.core.market_hours import calc_trading_seconds


@dataclass
class SellSignalV2:
    exit_reason: ExitReason     # 触发原因（枚举）
    sell_ratio: float           # 相对当前持仓的卖出比例（0~1）
    reason: str                 # 人类可读说明


def check_sell_signal(
    portfolio: PortfolioPosition,
    ctx,
    current_ts_ms: int = 0,
) -> Optional[SellSignalV2]:
    """
    检查是否触发组合止盈信号（V2）。

    优先级：tp1 > tp2 > 追踪止盈（EMA跌破）

    Args:
        portfolio: 当前 T仓组合持仓
        ctx: MarketContext（或 duck-type 兼容对象），需提供
             ctx.price、ctx.market_state、ctx.indicators.ema_5m_20 和 ctx.indicators.ema_2h_20
        current_ts_ms: 当前时间戳（毫秒），用于计算满仓超时；传 0 则不触发超时逻辑

    Returns:
        SellSignalV2 实例，或 None（无信号）
    """
    if portfolio.is_empty():
        return None

    price: float = ctx.price
    market_state: MarketState | None = getattr(ctx, "market_state", None)
    pnl: float = portfolio.pnl_pct(price)

    # TREND_UP 状态使用更高止盈阈值、更低分批卖出比例和 2H EMA20 追踪止盈
    is_trend_up: bool = market_state == MarketState.TREND_UP
    if is_trend_up:
        tp1_pct: float = config.TREND_TAKE_PROFIT_1_PCT
        tp2_pct: float = config.TREND_TAKE_PROFIT_2_PCT
        tp1_ratio: float = config.TREND_TP1_SELL_RATIO
        tp2_ratio: float = config.TREND_TP2_SELL_RATIO
        trailing_ema: float = ctx.indicators.ema_2h_20
        ema_label: str = "2小时EMA20"
    else:
        tp1_pct = config.TAKE_PROFIT_1_PCT
        tp2_pct = config.TAKE_PROFIT_2_PCT
        tp1_ratio = config.TAKE_PROFIT_1_SELL_RATIO
        tp2_ratio = config.TAKE_PROFIT_2_SELL_RATIO
        trailing_ema = ctx.indicators.ema_5m_20
        ema_label = "5分钟EMA20"

        # 满仓超时：非 TREND_UP 且满仓超过 24 交易小时，降低 TP1 阈值
        if (
            not portfolio.tp1_done
            and portfolio.full_since_ts is not None
            and current_ts_ms > 0
        ):
            trading_secs = calc_trading_seconds(portfolio.full_since_ts, current_ts_ms)
            if trading_secs >= config.FULL_POSITION_TIMEOUT_HOURS * 3600:
                tp1_pct = config.FULL_POSITION_TIMEOUT_TP1_PCT

    # 第1次止盈：达到当前市场状态对应的盈利阈值后，卖出对应比例
    if not portfolio.tp1_done and pnl >= tp1_pct:
        timeout_note = "（满仓超时降低阈值）" if tp1_pct == config.FULL_POSITION_TIMEOUT_TP1_PCT else ""
        return SellSignalV2(
            exit_reason=ExitReason.TAKE_PROFIT_1,
            sell_ratio=tp1_ratio,
            reason=f"T仓整体盈利{pnl:.2%}≥{tp1_pct:.2%}，卖出{tp1_ratio:.0%}{timeout_note}",
        )

    # 第2次止盈：tp1 已执行且达到阈值后，按初始仓位比例折算为当前剩余仓位卖出比例
    if portfolio.tp1_done and not portfolio.tp2_done and pnl >= tp2_pct:
        actual_sell_ratio = tp2_ratio / (1 - tp1_ratio)
        return SellSignalV2(
            exit_reason=ExitReason.TAKE_PROFIT_2,
            sell_ratio=actual_sell_ratio,
            reason=f"T仓整体盈利{pnl:.2%}≥{tp2_pct:.2%}，卖出初始仓位的{tp2_ratio:.0%}",
        )

    # 第3次止盈（追踪）：tp1 和 tp2 均已执行，金价跌破对应 EMA 后清空剩余持仓
    if portfolio.tp1_done and portfolio.tp2_done and price < trailing_ema:
        return SellSignalV2(
            exit_reason=ExitReason.TAKE_PROFIT_TRAILING,
            sell_ratio=1.0,
            reason=f"金价{price:.2f}跌破{ema_label}={trailing_ema:.2f}，清空剩余持仓",
        )

    return None
