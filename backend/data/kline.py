# backend/data/kline.py
import pandas as pd

_COLS = ["ts", "open", "high", "low", "close", "volume"]


def build_kline(ticks: list[dict], period_sec: int) -> pd.DataFrame:
    if not ticks:
        return pd.DataFrame(columns=_COLS)
    df = pd.DataFrame(ticks)
    df["dt"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.set_index("dt").sort_index()
    rule = f"{period_sec}s"
    ohlc = df["price"].resample(rule).ohlc().dropna()
    ohlc["volume"] = df["price"].resample(rule).count()
    ohlc = ohlc.reset_index()
    ohlc["ts"] = (ohlc["dt"].astype("int64") // 10**6).astype(int)
    return ohlc[_COLS].reset_index(drop=True)
