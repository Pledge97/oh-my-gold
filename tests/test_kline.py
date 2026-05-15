# tests/test_kline.py
import pytest
import pandas as pd
from backend.data.kline import build_kline


def make_ticks(n: int, base_price: float = 1000.0, start_ms: int = 1700000000000,
               interval_ms: int = 5000):
    return [{"ts": start_ms + i * interval_ms, "price": base_price + i * 0.1}
            for i in range(n)]


def test_build_kline_basic_columns():
    ticks = make_ticks(120)
    df = build_kline(ticks, period_sec=300)
    assert list(df.columns) == ["ts", "open", "high", "low", "close", "volume"]
    assert len(df) >= 1


def test_build_kline_ohlc_correct():
    ticks = [
        {"ts": 1700000000000, "price": 1000.0},
        {"ts": 1700000005000, "price": 1005.0},
        {"ts": 1700000010000, "price": 998.0},
        {"ts": 1700000015000, "price": 1002.0},
    ]
    df = build_kline(ticks, period_sec=60)
    assert df.iloc[0]["open"] == 1000.0
    assert df.iloc[0]["high"] == 1005.0
    assert df.iloc[0]["low"] == 998.0
    assert df.iloc[0]["close"] == 1002.0


def test_build_kline_empty_returns_empty():
    df = build_kline([], period_sec=300)
    assert df.empty
    assert list(df.columns) == ["ts", "open", "high", "low", "close", "volume"]
