# backend/indicators/rsi.py
import pandas as pd
from ta.momentum import RSIIndicator


def calc_rsi(df: pd.DataFrame, period: int = 14) -> float:
    return float(RSIIndicator(df["close"], window=period).rsi().iloc[-1])
