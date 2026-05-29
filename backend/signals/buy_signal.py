# backend/signals/buy_signal.py
from dataclasses import dataclass
from typing import Optional
from backend.core.context import MarketContext
from backend.core.enums import MarketState, SignalType
from backend import config


@dataclass
class BuySignalV2:
    """V2 建仓/加仓信号"""
    signal_type: SignalType   # BUY（初始建仓）或 ADD_LOT（加仓）
    amount_g: float           # 本次买入克数
    reason: str               # 触发原因描述


def _is_reentry_cooling_down(ctx, portfolio) -> bool:
    """
    判断最近卖出后是否仍处于买回冷却期。

    参数：
        ctx: MarketContext，包含 price、ts、indicators.atr_5m
        portfolio: PortfolioPosition，包含最近一次卖出信息

    返回：
        True 表示应阻止本次买入，False 表示允许继续检查买入条件
    """
    last_sell_ts = getattr(portfolio, "last_sell_ts", None)
    last_sell_price = getattr(portfolio, "last_sell_price", None)
    if last_sell_ts is None or last_sell_price is None:
        return False

    atr = max(getattr(ctx.indicators, "atr_5m", 0.0), 0.0)
    required_price_gap = max(
        config.REENTRY_MIN_PRICE_GAP,
        config.REENTRY_PRICE_GAP_ATR_MULTIPLIER * atr,
    )
    if ctx.price <= last_sell_price - required_price_gap:
        return False

    current_ts = getattr(ctx, "ts", 0) or 0
    if current_ts <= 0:
        return True

    elapsed_seconds = (current_ts - last_sell_ts) / 1000
    return elapsed_seconds < config.REENTRY_COOLDOWN_SECONDS


def check_buy_signal(
    ctx,
    portfolio,
    circuit_breaker_active: bool,
    last_buy_price: Optional[float] = None,
) -> Optional[BuySignalV2]:
    """
    检查是否触发建仓/加仓信号（V2 组合仓位版）。

    参数：
        ctx: MarketContext，包含 price、market_state、indicators
        portfolio: PortfolioPosition，当前组合持仓
        circuit_breaker_active: 熔断是否激活
        last_buy_price: 上一批次的买入价，用于判断加仓间距

    返回：
        BuySignalV2 或 None（无信号）
    """
    # 熔断激活时禁止建仓
    if circuit_breaker_active:
        return None

    # 刚止盈/止损后禁止按近似卖出价买回，避免反复支付手续费
    if _is_reentry_cooling_down(ctx, portfolio):
        return None

    # 浮亏超过阈值时停止加仓
    pnl = portfolio.pnl_pct(ctx.price)
    if pnl <= config.STOP_ADD_LOSS_PCT:
        return None

    state = ctx.market_state

    if state in (MarketState.OSCILLATION, MarketState.TREND_DECAY):
        return _check_oscillation_buy(ctx, portfolio, last_buy_price)

    if state == MarketState.TREND_UP:
        return _check_trend_buy(ctx, portfolio, last_buy_price)

    # TREND_DOWN 及其他状态：禁止建仓
    return None


def _next_target_amount_g(current_amount_g: float) -> float | None:
    """
    根据当前持仓克数返回下一档目标持仓量。超过最大仓位返回 None。

    参数：
        current_amount_g: 当前持仓克数

    返回：
        下一档目标克数（LOT1=50g、LOT1+LOT2=80g、T_MAX=100g），或 None（已满仓）
    """
    # 空仓或不足第1批：目标第1批（LOT1_AMOUNT_G）
    if current_amount_g <= 0:
        return config.LOT1_AMOUNT_G
    # 持仓未到第1批目标：补到第1批
    if current_amount_g < config.LOT1_AMOUNT_G:
        return config.LOT1_AMOUNT_G
    # 持仓第1批但未到第1+2批：目标第1+2批
    if current_amount_g < config.LOT1_AMOUNT_G + config.LOT2_AMOUNT_G:
        return config.LOT1_AMOUNT_G + config.LOT2_AMOUNT_G
    # 持仓第1+2批但未满仓：目标最大仓位
    if current_amount_g < config.T_MAX_AMOUNT_G:
        return config.T_MAX_AMOUNT_G
    # 已满仓，不再加仓
    return None


def _check_oscillation_buy(
    ctx,
    portfolio,
    last_buy_price: Optional[float],
) -> Optional[BuySignalV2]:
    """
    震荡/趋势衰减模式建仓逻辑：
    - 空仓：价格 ≤ 布林下轨 → 第1批（LOT1_AMOUNT_G）
    - 持仓1批：价格从上次买入跌 ATR_ADD_LOT_MULTIPLIER×atr_5m → 第2批（LOT2_AMOUNT_G）
    - 持仓2批：价格从上次买入再跌同样间距 → 第3批（LOT3_AMOUNT_G）
    - 满仓（≥T_MAX_AMOUNT_G）：不加仓
    """
    price = ctx.price
    bb_lower = ctx.indicators.bb_lower
    atr = max(ctx.indicators.atr_5m, 5.0)  # 最小5元，避免加仓间距过小

    if portfolio.is_empty():
        # 空仓：触及布林下轨才建仓
        if price <= bb_lower:
            return BuySignalV2(
                signal_type=SignalType.BUY,
                amount_g=config.LOT1_AMOUNT_G,
                reason=f"价格{price:.2f}触及布林下轨{bb_lower:.2f}，初始建仓",
            )
        return None

    # 已有持仓：检查是否满仓
    if portfolio.total_amount_g >= config.T_MAX_AMOUNT_G:
        return None

    # 持仓不足首批时，按空仓建仓价格补回第一档，不再沿用上次买入价下跌间距。
    if portfolio.total_amount_g < config.LOT1_AMOUNT_G:
        if price <= bb_lower:
            target_amount_g = config.LOT1_AMOUNT_G
            amount_g = round(target_amount_g - portfolio.total_amount_g, 4)
            return BuySignalV2(
                signal_type=SignalType.ADD_LOT,
                amount_g=amount_g,
                reason=f"价格{price:.2f}触及布林下轨{bb_lower:.2f}，补仓至{target_amount_g:.0f}g",
            )
        return None

    # 需要上次买入价才能判断加仓间距
    if last_buy_price is None:
        return None

    required_drop = config.ATR_ADD_LOT_MULTIPLIER * atr
    if price <= last_buy_price - required_drop:
        # 根据当前持仓量确定目标档位，计算本次加仓克数
        target_amount_g = _next_target_amount_g(portfolio.total_amount_g)
        if target_amount_g is None:
            return None
        # 本次加仓克数 = 目标档位 − 当前持仓
        amount_g = round(target_amount_g - portfolio.total_amount_g, 4)
        # 根据当前持仓确定信号类型（防御性处理：有仓位才用 ADD_LOT）
        sig_type = SignalType.BUY if portfolio.is_empty() else SignalType.ADD_LOT
        return BuySignalV2(
            signal_type=sig_type,
            amount_g=amount_g,
            reason=f"价格从{last_buy_price:.2f}跌{required_drop:.2f}，补仓至{target_amount_g:.0f}g",
        )

    return None


def _check_trend_buy(
    ctx,
    portfolio,
    last_buy_price: Optional[float],
) -> Optional[BuySignalV2]:
    """
    趋势上涨模式建仓逻辑：
    - 空仓：4H EMA20 > EMA60 且 RSI ≤ TREND_RSI_OVERSOLD → 第1批
    - 有仓：加仓规则同震荡模式
    """
    ind = ctx.indicators

    # 趋势确认：4H EMA20 必须在 EMA60 之上
    if ind.ema_4h_20 <= ind.ema_4h_60:
        return None

    if portfolio.is_empty():
        # 空仓：RSI 超卖才建仓
        if ind.rsi <= config.TREND_RSI_OVERSOLD:
            return BuySignalV2(
                signal_type=SignalType.BUY,
                amount_g=config.LOT1_AMOUNT_G,
                reason=f"趋势上涨，RSI={ind.rsi:.1f}回调超卖，初始建仓",
            )
        return None

    # 有仓时加仓规则同震荡模式
    return _check_oscillation_buy(ctx, portfolio, last_buy_price)


def get_next_buy_price(portfolio, ctx) -> float | None:
    """
    获取下一次买入触发价格，用于前端展示。

    Args:
        portfolio: 当前持仓
        ctx: MarketContext（需包含 indicators.bb_lower, indicators.atr_5m, last_buy_price）

    Returns:
        下一次买入触发价格，满仓时返回 None
    """
    if portfolio.total_amount_g >= config.T_MAX_AMOUNT_G:
        return None

    if _is_reentry_cooling_down(ctx, portfolio):
        return None

    if portfolio.is_empty():
        return ctx.indicators.bb_lower or None

    if portfolio.total_amount_g < config.LOT1_AMOUNT_G:
        return ctx.indicators.bb_lower or None

    atr = max(ctx.indicators.atr_5m, 5.0)
    if portfolio.last_buy_price:
        return round(portfolio.last_buy_price - config.ATR_ADD_LOT_MULTIPLIER * atr, 2)

    return None
