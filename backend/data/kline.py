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
    ohlc = df["price"].resample(rule).ohlc()
    vol = df["price"].resample(rule).count()

    # 用前收盘价填充无 tick 的时间槽（flat bar），保持序列连续
    ohlc["close"] = ohlc["close"].ffill()
    ohlc["open"] = ohlc["open"].fillna(ohlc["close"])
    ohlc["high"] = ohlc["high"].fillna(ohlc["close"])
    ohlc["low"] = ohlc["low"].fillna(ohlc["close"])
    ohlc = ohlc.dropna()  # 仍丢弃序列最开头还没有任何数据的槽

    ohlc["volume"] = vol.reindex(ohlc.index).fillna(0)
    ohlc = ohlc.reset_index()
    ohlc["ts"] = (ohlc["dt"].astype("int64") // 10**6).astype(int)
    return ohlc[_COLS].reset_index(drop=True)
