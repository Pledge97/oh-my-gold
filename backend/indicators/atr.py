# backend/indicators/atr.py
import pandas as pd
from ta.volatility import AverageTrueRange


def calc_atr(df: pd.DataFrame, period: int = 14) -> float:
    return float(AverageTrueRange(df["high"], df["low"], df["close"], window=period).average_true_range().iloc[-1])
