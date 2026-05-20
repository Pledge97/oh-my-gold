# backend/core/context.py
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

from backend.core.enums import MarketState


@dataclass
class IndicatorSnapshot:
    adx: float = 0.0
    plus_di: float = 0.0
    minus_di: float = 0.0
    adx_series: Optional[pd.Series] = None
    bb_upper: float = 0.0
    bb_mid: float = 0.0
    bb_lower: float = 0.0
    rsi: float = 50.0
    atr_5m: float = 0.0
    atr_daily_mean: float = 0.0
    ema_5m_20: float = 0.0
    ema_4h_20: float = 0.0
    ema_4h_60: float = 0.0
    ema_2h_20: float = 0.0  # 2小时 EMA20，用于 TREND_UP 追踪止盈


@dataclass
class MarketContext:
    price: float = 0.0
    prev_price: float = 0.0
    price_5m_ago: float = 0.0
    ts: int = 0
    market_state: MarketState = MarketState.OSCILLATION
    indicators: IndicatorSnapshot = field(default_factory=IndicatorSnapshot)
    kline_5m: Optional[pd.DataFrame] = None
    kline_4h: Optional[pd.DataFrame] = None
    kline_daily: Optional[pd.DataFrame] = None
    ready: bool = False  # 数据是否足够启动策略


# 全局单例
ctx = MarketContext()
