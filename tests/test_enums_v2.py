# tests/test_enums_v2.py
from backend.core.enums import ExitReason, LotStatus, SignalType

def test_exit_reason_values():
    assert ExitReason.TAKE_PROFIT_1.value == "TAKE_PROFIT_1"
    assert ExitReason.TAKE_PROFIT_2.value == "TAKE_PROFIT_2"
    assert ExitReason.TAKE_PROFIT_TRAILING.value == "TAKE_PROFIT_TRAILING"
    assert ExitReason.STOP_LOSS_HALF.value == "STOP_LOSS_HALF"
    assert ExitReason.STOP_LOSS_CLEAR.value == "STOP_LOSS_CLEAR"
    assert ExitReason.TREND_CLEAR.value == "TREND_CLEAR"
    assert ExitReason.OVERNIGHT_TRAILING.value == "OVERNIGHT_TRAILING"

def test_lot_status_values():
    assert LotStatus.OPEN.value == "OPEN"
    assert LotStatus.CLOSED.value == "CLOSED"

def test_signal_type_has_add_lot():
    assert SignalType.ADD_LOT.value == "ADD_LOT"
    assert SignalType.STOP_ADD.value == "STOP_ADD"
