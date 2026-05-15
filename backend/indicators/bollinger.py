# backend/indicators/bollinger.py
import pandas as pd
from ta.volatility import BollingerBands


def calc_bollinger(df: pd.DataFrame, period: int = 20, std: float = 2.0) -> dict:
    ind = BollingerBands(df["close"], window=period, window_dev=std)
    return {
        "upper": float(ind.bollinger_hband().iloc[-1]),
        "mid":   float(ind.bollinger_mavg().iloc[-1]),
        "lower": float(ind.bollinger_lband().iloc[-1]),
    }
