# tests/test_indicators.py
import pytest
import pandas as pd
import numpy as np
from backend.indicators.adx import calc_adx
from backend.indicators.bollinger import calc_bollinger
from backend.indicators.rsi import calc_rsi
from backend.indicators.atr import calc_atr
from backend.indicators.ema import calc_ema


def make_ohlc(n=60, seed=42):
    np.random.seed(seed)
    c = 1000 + np.cumsum(np.random.randn(n) * 2)
    return pd.DataFrame({"open": c-1, "high": c+3, "low": c-3, "close": c})


def test_calc_adx_keys_and_range():
    result = calc_adx(make_ohlc(60), period=14)
    assert set(result.keys()) == {"adx", "plus_di", "minus_di", "adx_series"}
    assert 0 <= result["adx"] <= 100


def test_calc_bollinger_ordering():
    result = calc_bollinger(make_ohlc(50), period=20, std=2.0)
    assert result["upper"] > result["mid"] > result["lower"]


def test_calc_rsi_range():
    assert 0 <= calc_rsi(make_ohlc(50), period=14) <= 100


def test_calc_atr_positive():
    assert calc_atr(make_ohlc(30), period=14) > 0


def test_calc_ema_no_nan_at_end():
    s = calc_ema(make_ohlc(100), period=20)
    assert not pd.isna(s.iloc[-1])
