# backend/core/scheduler.py
import time
from collections import deque
from datetime import date

import pandas as pd

from backend.core.context import MarketContext, IndicatorSnapshot, ctx
from backend.core.event_bus import bus
from backend.core.market_hours import is_trading_time
from backend.data.fetcher_tick import run_once as fetch_tick
from backend.data.kline import build_kline
from backend.db.database import get_conn
from backend.indicators.adx import calc_adx
from backend.indicators.atr import calc_atr
from backend.indicators.bollinger import calc_bollinger
from backend.indicators.ema import calc_ema
from backend.indicators.rsi import calc_rsi
from backend.signals.regime_signal import detect_regime
from backend import config

# ── 缓存配置 ──────────────────────────────────────────────────
# tick 内存缓存最大保留天数（覆盖4H EMA60所需10天，留余量）
_TICK_CACHE_DAYS = 15
_TICK_CACHE_MS = _TICK_CACHE_DAYS * 86400 * 1000

# 慢速指标刷新间隔（秒）
_4H_REFRESH_SEC = 3600    # 4小时K线每小时重建一次

# ── 内存缓存 ──────────────────────────────────────────────────
# tick 缓存：deque 保证 O(1) 头部清理
_tick_cache: deque[dict] = deque()

# 慢速指标缓存
_kline_4h_cache: pd.DataFrame = pd.DataFrame()
_daily_df_cache: pd.DataFrame = pd.DataFrame()
_ema_4h_20_cache: float = 0.0
_ema_4h_60_cache: float = 0.0
_adx_cache: dict = {"adx": 0.0, "plus_di": 0.0, "minus_di": 0.0, "adx_series": None}
_atr_daily_mean_cache: float = 0.0

# 上次慢速刷新时间
_last_4h_refresh: float = 0.0
_last_daily_refresh_date: date = date.min  # 上次日线刷新的日期


def _init_tick_cache() -> None:
    """服务启动时从数据库加载历史 tick 到内存缓存，并立即初始化慢速指标"""
    global _tick_cache
    since_ms = int((time.time() - _TICK_CACHE_DAYS * 86400) * 1000)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ts, price FROM prices WHERE ts >= ? ORDER BY ts ASC",
            (since_ms,),
        ).fetchall()
    _tick_cache = deque({"ts": r["ts"], "price": r["price"]} for r in rows)
    print(f"[scheduler] tick 缓存初始化：{len(_tick_cache)} 条")
    # 立即初始化慢速指标，不等第一个 tick 到来
    _refresh_slow_indicators(time.time())


def _append_tick(ts: int, price: float) -> None:
    """追加新 tick，并清理超出保留期的旧数据"""
    _tick_cache.append({"ts": ts, "price": price})
    cutoff_ms = ts - _TICK_CACHE_MS
    while _tick_cache and _tick_cache[0]["ts"] < cutoff_ms:
        _tick_cache.popleft()


def _load_daily_df() -> pd.DataFrame:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT open, high, low, close FROM daily_prices ORDER BY date ASC"
        ).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def _refresh_slow_indicators(now: float) -> None:
    """按频率刷新4H K线和日线指标，避免每5秒全量重算"""
    global _kline_4h_cache, _ema_4h_20_cache, _ema_4h_60_cache
    global _daily_df_cache, _adx_cache, _atr_daily_mean_cache
    global _last_4h_refresh, _last_daily_refresh_date

    ticks = list(_tick_cache)

    # 4H K线：每小时重建
    if now - _last_4h_refresh >= _4H_REFRESH_SEC:
        _kline_4h_cache = build_kline(ticks, period_sec=14400)
        if not _kline_4h_cache.empty and len(_kline_4h_cache) >= config.EMA_LONG:
            _ema_4h_20_cache = float(calc_ema(_kline_4h_cache, config.EMA_SHORT).iloc[-1])
            _ema_4h_60_cache = float(calc_ema(_kline_4h_cache, config.EMA_LONG).iloc[-1])
        else:
            _ema_4h_20_cache = _ema_4h_60_cache = 0.0
        _last_4h_refresh = now

    # 日线ADX：每天 00:01 后首次 tick 时刷新
    today = date.today()
    t = time.localtime()
    past_midnight = t.tm_hour > 0 or t.tm_min >= 1
    if today != _last_daily_refresh_date and past_midnight:
        _daily_df_cache = _load_daily_df()
        min_daily = config.ADX_PERIOD + config.ADX_LOOKBACK + 1
        if len(_daily_df_cache) >= min_daily:
            _adx_cache = calc_adx(_daily_df_cache, config.ADX_PERIOD)
        if len(_daily_df_cache) >= config.ATR_PERIOD * 2:
            _atr_daily_mean_cache = calc_atr(_daily_df_cache, config.ATR_PERIOD)
        _last_daily_refresh_date = today


def _update_context(price: float, ts: int) -> None:
    now = time.time()

    # 追加新 tick 到内存缓存（同时清理过期数据）
    _append_tick(ts, price)

    # 刷新慢速指标（按频率，不是每5秒）
    _refresh_slow_indicators(now)

    # 5分钟K线：每次用全量 tick 重建（只需最近几百根，速度快）
    ticks = list(_tick_cache)
    kline_5m = build_kline(ticks, period_sec=300)

    ctx.price = price
    ctx.ts = ts
    ctx.prev_price = ctx.price
    ctx.ready = False

    min_daily = config.ADX_PERIOD + config.ADX_LOOKBACK + 1
    min_5m = max(config.BB_PERIOD, config.ATR_PERIOD, config.RSI_PERIOD, config.EMA_SHORT)

    if (len(_daily_df_cache) >= min_daily
            and not kline_5m.empty
            and len(kline_5m) >= min_5m):

        bb = calc_bollinger(kline_5m, config.BB_PERIOD, config.BB_STD)
        rsi = calc_rsi(kline_5m, config.RSI_PERIOD)
        atr_5m = calc_atr(kline_5m, config.ATR_PERIOD)
        ema_5m_20 = float(calc_ema(kline_5m, config.EMA_SHORT).iloc[-1])

        ctx.indicators = IndicatorSnapshot(
            adx=_adx_cache["adx"],
            plus_di=_adx_cache["plus_di"],
            minus_di=_adx_cache["minus_di"],
            adx_series=_adx_cache["adx_series"],
            bb_upper=bb["upper"],
            bb_mid=bb["mid"],
            bb_lower=bb["lower"],
            rsi=rsi,
            atr_5m=atr_5m,
            atr_daily_mean=_atr_daily_mean_cache,
            ema_5m_20=ema_5m_20,
            ema_4h_20=_ema_4h_20_cache,
            ema_4h_60=_ema_4h_60_cache,
        )
        ctx.market_state = detect_regime(ctx)
        ctx.ready = True

    # 5分钟前价格（用于一级熔断）
    if len(ticks) >= 60:
        ctx.price_5m_ago = ticks[-60]["price"]

    ctx.kline_5m = kline_5m
    ctx.kline_4h = _kline_4h_cache
    ctx.kline_daily = _daily_df_cache


async def tick_job(engine, broadcast_fn) -> None:
    if not is_trading_time():
        await broadcast_fn({"is_market_open": False})
        return

    price = fetch_tick()
    if price is None:
        return

    ts = int(time.time() * 1000)
    _update_context(price, ts)
    bus.publish("tick", {"price": price, "ts": ts})

    result = engine.on_tick_v2(ctx)
    result["is_market_open"] = True
    await broadcast_fn(result)
