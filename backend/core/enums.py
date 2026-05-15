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
    ADD_LOT     = "ADD_LOT"      # 加仓信号
    STOP_ADD    = "STOP_ADD"     # 停止加仓信号


class CloseType(Enum):
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS   = "STOP_LOSS"


class ExitReason(str, Enum):
    """清仓/减仓原因"""
    TAKE_PROFIT_1 = "TAKE_PROFIT_1"          # 盈利≥0.6%，卖出60%
    TAKE_PROFIT_2 = "TAKE_PROFIT_2"          # 盈利≥1.2%，卖出20%
    TAKE_PROFIT_TRAILING = "TAKE_PROFIT_TRAILING"  # EMA跌破，清空剩余
    STOP_LOSS_HALF = "STOP_LOSS_HALF"        # 亏损≥-2.5%，减仓50%
    STOP_LOSS_CLEAR = "STOP_LOSS_CLEAR"      # 亏损≥-3.5%，全部清仓
    TREND_CLEAR = "TREND_CLEAR"              # 趋势转空，立即清仓
    OVERNIGHT_TRAILING = "OVERNIGHT_TRAILING"  # 隔夜追踪止损


class LotStatus(str, Enum):
    """单批次仓位状态"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class TradingMode(Enum):
    OSCILLATION = "OSCILLATION"
    TREND       = "TREND"
