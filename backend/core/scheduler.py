# backend/core/scheduler.py
import time
import pandas as pd
from backend.core.context import MarketContext, IndicatorSnapshot, ctx
from backend.core.event_bus import bus
from backend.data.fetcher_tick import run_once as fetch_tick
from backend.data.kline import build_kline
from backend.db.database import get_conn
from backend.indicators.adx import calc_adx
from backend.indicators.bollinger import calc_bollinger
from backend.indicators.rsi import calc_rsi
from backend.indicators.atr import calc_atr
from backend.indicators.ema import calc_ema
from backend.signals.regime_signal import detect_regime
from backend import config


def _load_ticks(limit: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ts, price FROM prices ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
    return [{"ts": r["ts"], "price": r["price"]} for r in reversed(rows)]


def _load_daily_df() -> pd.DataFrame:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT open, high, low, close FROM daily_prices ORDER BY date ASC"
        ).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def _update_context(price: float) -> None:
    ticks = _load_ticks(100_000)
    kline_5m = build_kline(ticks, period_sec=300)
    kline_4h = build_kline(ticks, period_sec=14400)
    daily_df = _load_daily_df()

    ctx.price = price
    ctx.ts = int(time.time() * 1000)
    ctx.prev_price = ctx.price
    ctx.ready = False

    min_daily = config.ADX_PERIOD + config.ADX_LOOKBACK + 1
    min_5m = max(config.BB_PERIOD, config.ATR_PERIOD, config.RSI_PERIOD, config.EMA_SHORT)

    if (len(daily_df) >= min_daily
            and not kline_5m.empty
            and len(kline_5m) >= min_5m):

        adx_res = calc_adx(daily_df, config.ADX_PERIOD)
        bb = calc_bollinger(kline_5m, config.BB_PERIOD, config.BB_STD)
        rsi = calc_rsi(kline_5m, config.RSI_PERIOD)
        atr_5m = calc_atr(kline_5m, config.ATR_PERIOD)
        ema_5m_20 = float(calc_ema(kline_5m, config.EMA_SHORT).iloc[-1])

        # 日线ATR均值（用于二级熔断）
        atr_daily_mean = 0.0
        if len(daily_df) >= config.ATR_PERIOD * 2:
            atr_daily = calc_atr(daily_df, config.ATR_PERIOD)
            atr_daily_mean = atr_daily

        ema_4h_20 = ema_4h_60 = 0.0
        if not kline_4h.empty and len(kline_4h) >= config.EMA_LONG:
            ema_4h_20 = float(calc_ema(kline_4h, config.EMA_SHORT).iloc[-1])
            ema_4h_60 = float(calc_ema(kline_4h, config.EMA_LONG).iloc[-1])

        ctx.indicators = IndicatorSnapshot(
            adx=adx_res["adx"],
            plus_di=adx_res["plus_di"],
            minus_di=adx_res["minus_di"],
            adx_series=adx_res["adx_series"],
            bb_upper=bb["upper"],
            bb_mid=bb["mid"],
            bb_lower=bb["lower"],
            rsi=rsi,
            atr_5m=atr_5m,
            atr_daily_mean=atr_daily_mean,
            ema_5m_20=ema_5m_20,
            ema_4h_20=ema_4h_20,
            ema_4h_60=ema_4h_60,
        )
        ctx.market_state = detect_regime(ctx)
        ctx.ready = True

    # 5分钟前价格（用于一级熔断）
    if len(ticks) >= 60:
        ctx.price_5m_ago = ticks[-60]["price"]

    ctx.kline_5m = kline_5m
    ctx.kline_4h = kline_4h
    ctx.kline_daily = daily_df


async def tick_job(engine, broadcast_fn) -> None:
    price = fetch_tick()
    if price is None:
        return

    _update_context(price)
    bus.publish("tick", {"price": price, "ts": int(time.time() * 1000)})

    result = engine.on_tick_v2(ctx)
    await broadcast_fn(result)
