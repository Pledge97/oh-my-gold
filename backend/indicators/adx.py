# backend/indicators/adx.py
import pandas as pd
from ta.trend import ADXIndicator


def calc_adx(df: pd.DataFrame, period: int = 14) -> dict:
    ind = ADXIndicator(df["high"], df["low"], df["close"], window=period)
    return {
        "adx":        float(ind.adx().iloc[-1]),
        "plus_di":    float(ind.adx_pos().iloc[-1]),
        "minus_di":   float(ind.adx_neg().iloc[-1]),
        "adx_series": ind.adx(),
    }
