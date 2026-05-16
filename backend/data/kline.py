# backend/data/kline.py
import pandas as pd
from dataclasses import dataclass
from typing import Optional

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
    ohlc = ohlc.dropna()  # 丢弃序列最开头还没有任何数据的槽

    ohlc["volume"] = vol.reindex(ohlc.index).fillna(0)
    ohlc = ohlc.reset_index()
    ohlc["ts"] = (ohlc["dt"].astype("int64") // 10**6).astype(int)
    return ohlc[_COLS].reset_index(drop=True)


@dataclass
class _Bar:
    """单根K线"""
    ts: int        # 窗口起始时间（毫秒）
    open: float
    high: float
    low: float
    close: float
    volume: int = 0


class KlineBuilder:
    """
    增量K线构建器，O(1) 更新当前K线。
    跨窗口时自动封闭旧K线并补全缺口（flat bar）。
    服务启动时用 build_kline 的历史结果初始化，之后每个 tick 增量更新。
    """

    def __init__(self, period_sec: int, history: Optional[pd.DataFrame] = None):
        self._period_ms = period_sec * 1000
        self._finished: list[_Bar] = []
        self._current: Optional[_Bar] = None

        if history is not None and not history.empty:
            for _, row in history.iterrows():
                self._finished.append(_Bar(
                    ts=int(row["ts"]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(row["volume"]),
                ))
            # 最后一根可能是未完成的，移出作为 current
            if self._finished:
                self._current = self._finished.pop()

    def _window_ts(self, ts_ms: int) -> int:
        """计算 ts_ms 所属窗口的起始时间（秒，与 build_kline 对齐）"""
        period_sec = self._period_ms // 1000
        ts_sec = ts_ms // 1000
        return (ts_sec // period_sec) * period_sec

    def _fill_gaps(self, from_ts: int, to_ts: int) -> None:
        """在两个窗口之间补充 flat bar（ts 单位：秒）"""
        if not self._finished:
            return
        prev_close = self._finished[-1].close
        period_sec = self._period_ms // 1000
        cur = from_ts + period_sec
        while cur < to_ts:
            self._finished.append(_Bar(
                ts=cur, open=prev_close, high=prev_close,
                low=prev_close, close=prev_close, volume=0,
            ))
            cur += period_sec

    def update(self, ts_ms: int, price: float) -> None:
        """处理一个新 tick，O(1)"""
        win_ts = self._window_ts(ts_ms)  # 秒

        if self._current is None:
            self._current = _Bar(ts=win_ts, open=price, high=price,
                                  low=price, close=price, volume=1)
            return

        if win_ts == self._current.ts:
            self._current.high = max(self._current.high, price)
            self._current.low = min(self._current.low, price)
            self._current.close = price
            self._current.volume += 1
        else:
            # 跨窗口：封闭当前K线，补 flat bar，开启新K线
            self._finished.append(self._current)
            self._fill_gaps(self._current.ts, win_ts)
            self._current = _Bar(ts=win_ts, open=price, high=price,
                                  low=price, close=price, volume=1)

    def to_dataframe(self) -> pd.DataFrame:
        """返回完整K线 DataFrame（历史 + 当前未完成K线），ts 单位秒，与 build_kline 一致"""
        bars = self._finished.copy()
        if self._current is not None:
            bars.append(self._current)
        if not bars:
            return pd.DataFrame(columns=_COLS)
        return pd.DataFrame([
            {"ts": b.ts, "open": b.open, "high": b.high,
             "low": b.low, "close": b.close, "volume": b.volume}
            for b in bars
        ])

    def trim(self, cutoff_ms: int) -> None:
        """清理早于 cutoff_ms 的已完成K线（cutoff_ms 转换为秒比较）"""
        cutoff_sec = cutoff_ms // 1000
        while self._finished and self._finished[0].ts < cutoff_sec:
            self._finished.pop(0)
