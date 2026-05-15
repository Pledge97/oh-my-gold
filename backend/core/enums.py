# backend/core/enums.py
from enum import Enum


class MarketState(Enum):
    OSCILLATION  = "OSCILLATION"
    TREND_UP     = "TREND_UP"
    TREND_DOWN   = "TREND_DOWN"
    TREND_DECAY  = "TREND_DECAY"


class SignalType(Enum):
    BUY         = "BUY"
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS   = "STOP_LOSS"
    NONE        = "NONE"


class CloseType(Enum):
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS   = "STOP_LOSS"


class TradingMode(Enum):
    OSCILLATION = "OSCILLATION"
    TREND       = "TREND"
