# backend/signals/buy_signal.py
from dataclasses import dataclass
from typing import Optional
from backend.core.context import MarketContext
from backend.core.enums import MarketState, SignalType
from backend import config


@dataclass
class BuySignal:
    triggered: bool
    amount_g: float
    reason: str


def check_buy(ctx: MarketContext, open_positions: int, unit_g: float) -> BuySignal:
    """V1 建仓信号（保留兼容）"""
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


# ── V2 分批建仓信号 ────────────────────────────────────────

@dataclass
class BuySignalV2:
    """V2 建仓/加仓信号"""
    signal_type: SignalType   # BUY（初始建仓）或 ADD_LOT（加仓）
    amount_g: float           # 本次买入克数
    reason: str               # 触发原因描述


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
    atr = ctx.indicators.atr_5m

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

    # 需要上次买入价才能判断加仓间距
    if last_buy_price is None:
        return None

    required_drop = config.ATR_ADD_LOT_MULTIPLIER * atr
    if price <= last_buy_price - required_drop:
        lot_count = portfolio.lot_count
        if lot_count == 1:
            return BuySignalV2(
                signal_type=SignalType.ADD_LOT,
                amount_g=config.LOT2_AMOUNT_G,
                reason=f"价格从{last_buy_price:.2f}跌{required_drop:.2f}，第2批加仓",
            )
        if lot_count == 2:
            return BuySignalV2(
                signal_type=SignalType.ADD_LOT,
                amount_g=config.LOT3_AMOUNT_G,
                reason=f"价格从{last_buy_price:.2f}跌{required_drop:.2f}，第3批加仓",
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
