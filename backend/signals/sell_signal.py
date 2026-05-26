# backend/signals/sell_signal.py
from dataclasses import dataclass
from typing import Optional
from backend.core.enums import ExitReason, MarketState
from backend.risk.portfolio import PortfolioPosition
from backend import config
from backend.core.market_hours import calc_trading_seconds


def calc_trigger_price(avg_cost: float, pnl_pct: float) -> float:
    """
    根据平均成本和目标盈亏率，计算触发价格（扣除卖出手续费后达到目标盈亏）。

    Args:
        avg_cost: 平均成本价（元/g）
        pnl_pct: 目标盈亏率（如 0.006 表示 0.6%，-0.025 表示 -2.5%）

    Returns:
        触发价格（元/g），保留2位小数
    """
    return round(avg_cost * (1 + pnl_pct) / (1 - config.SELL_FEE_RATE), 2)


def get_next_tp_price(portfolio: PortfolioPosition, ctx) -> float | None:
    """
    获取下一次止盈触发价格。

    Args:
        portfolio: 当前持仓
        ctx: MarketContext（需包含 market_state, ts 等字段）

    Returns:
        下一次止盈触发价格，如果已完成所有止盈则返回 None
    """
    if portfolio.is_empty():
        return None

    market_state = getattr(ctx, "market_state", None)

    if not portfolio.tp1_done:
        # TP1 未完成：计算 TP1 触发价
        tp1_pct = config.TAKE_PROFIT_1_PCT
        if market_state == MarketState.TREND_UP:
            tp1_pct = config.TREND_TAKE_PROFIT_1_PCT
        elif (
            market_state != MarketState.TREND_UP
            and portfolio.full_since_ts is not None
            and portfolio.total_amount_g >= config.T_MAX_AMOUNT_G
            and getattr(ctx, "ts", None)
        ):
            # 满仓超时：使用降低后的 TP1 阈值
            trading_secs = calc_trading_seconds(portfolio.full_since_ts, ctx.ts)
            if trading_secs >= config.FULL_POSITION_TIMEOUT_HOURS * 3600:
                tp1_pct = config.FULL_POSITION_TIMEOUT_TP1_PCT
        return calc_trigger_price(portfolio.avg_cost, tp1_pct)

    elif not portfolio.tp2_done:
        # TP1 已完成，TP2 未完成：计算 TP2 触发价
        tp2_pct = config.TREND_TAKE_PROFIT_2_PCT if market_state == MarketState.TREND_UP else config.TAKE_PROFIT_2_PCT
        return calc_trigger_price(portfolio.avg_cost, tp2_pct)

    # TP2 已完成：追踪止盈无固定价格
    return None


def get_next_stop_price(portfolio: PortfolioPosition, current_pnl_pct: float) -> float | None:
    """
    获取下一次止损触发价格。

    Args:
        portfolio: 当前持仓
        current_pnl_pct: 当前盈亏率

    Returns:
        下一次止损触发价格，如果已触发清仓则返回 None
    """
    if portfolio.is_empty():
        return None

    if current_pnl_pct > config.FORCE_HALF_LOSS_PCT:
        # 当前盈亏 > -2.5%，显示第一档止损（减仓50%）
        return calc_trigger_price(portfolio.avg_cost, config.FORCE_HALF_LOSS_PCT)
    elif current_pnl_pct > config.CLEAR_ALL_LOSS_PCT:
        # 当前盈亏在 -2.5% 和 -3.5% 之间，显示第二档止损（清仓）
        return calc_trigger_price(portfolio.avg_cost, config.CLEAR_ALL_LOSS_PCT)

    # 当前盈亏 <= -3.5%，已触发清仓
    return None


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

    # 标记是否触发满仓超时逻辑
    timeout_triggered: bool = False

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
            and portfolio.total_amount_g >= config.T_MAX_AMOUNT_G
            and current_ts_ms > 0
        ):
            trading_secs = calc_trading_seconds(portfolio.full_since_ts, current_ts_ms)
            if trading_secs >= config.FULL_POSITION_TIMEOUT_HOURS * 3600:
                tp1_pct = config.FULL_POSITION_TIMEOUT_TP1_PCT
                timeout_triggered = True

    # 第1次止盈：达到当前市场状态对应的盈利阈值后，卖出对应比例
    if not portfolio.tp1_done and pnl >= tp1_pct:
        timeout_note = "（满仓超时降低阈值）" if timeout_triggered else ""
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
