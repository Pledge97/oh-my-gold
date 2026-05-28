# backend/signals/exit_signal.py
from dataclasses import dataclass
from typing import Optional
from backend.core.enums import MarketState, ExitReason
from backend.risk.portfolio import PortfolioPosition
from backend import config


@dataclass
class ExitSignalV2:
    exit_reason: ExitReason   # 触发原因枚举
    sell_ratio: float         # 卖出比例：0.0~1.0，相对当前持仓
    reason: str               # 人类可读的原因描述


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


def get_next_stop_price(portfolio: PortfolioPosition, current_pnl_pct: float) -> float | None:
    """
    获取下一次止损触发价格，用于前端展示。

    Args:
        portfolio: 当前持仓
        current_pnl_pct: 当前盈亏率

    Returns:
        下一次止损触发价格，如果已触发清仓则返回 None
    """
    if portfolio.is_empty():
        return None

    if portfolio.stop_loss_half_done:
        if current_pnl_pct > config.CLEAR_ALL_LOSS_PCT:
            return calc_trigger_price(portfolio.avg_cost, config.CLEAR_ALL_LOSS_PCT)
        return None

    if current_pnl_pct > config.FORCE_HALF_LOSS_PCT:
        return calc_trigger_price(portfolio.avg_cost, config.FORCE_HALF_LOSS_PCT)
    elif current_pnl_pct > config.CLEAR_ALL_LOSS_PCT:
        return calc_trigger_price(portfolio.avg_cost, config.CLEAR_ALL_LOSS_PCT)

    return None


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

    # 优先级3：亏损≥-2.5%，强制减仓50%，同一轮只执行一次
    if pnl <= config.FORCE_HALF_LOSS_PCT and not portfolio.stop_loss_half_done:
        return ExitSignalV2(
            exit_reason=ExitReason.STOP_LOSS_HALF,
            sell_ratio=0.50,
            reason=f"T仓浮亏{pnl:.2%}≤{config.FORCE_HALF_LOSS_PCT:.2%}，强制减仓50%",
        )

    return None
