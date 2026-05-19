# tests/test_config_v2.py
from backend.config import (
    LOT1_AMOUNT_G,
    LOT2_AMOUNT_G,
    LOT3_AMOUNT_G,
    T_MAX_AMOUNT_G,
    STOP_ADD_LOSS_PCT,
    FORCE_HALF_LOSS_PCT,
    CLEAR_ALL_LOSS_PCT,
    TAKE_PROFIT_1_PCT,
    TAKE_PROFIT_2_PCT,
    TAKE_PROFIT_1_SELL_RATIO,
    TAKE_PROFIT_2_SELL_RATIO,
    ATR_ADD_LOT_MULTIPLIER,
)

def test_lot_amounts_sum_to_max():
    assert LOT1_AMOUNT_G + LOT2_AMOUNT_G + LOT3_AMOUNT_G == T_MAX_AMOUNT_G

def test_loss_thresholds_ascending():
    assert STOP_ADD_LOSS_PCT > FORCE_HALF_LOSS_PCT > CLEAR_ALL_LOSS_PCT

def test_take_profit_thresholds():
    assert TAKE_PROFIT_1_PCT < TAKE_PROFIT_2_PCT
