# backend/indicators/ema.py
import pandas as pd
from ta.trend import EMAIndicator


def calc_ema(df: pd.DataFrame, period: int) -> pd.Series:
    return EMAIndicator(df["close"], window=period).ema_indicator()
