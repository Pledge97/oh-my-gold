# tests/test_enums_v2.py
from backend.core.enums import ExitReason, LotStatus, SignalType

def test_exit_reason_values():
    assert ExitReason.TAKE_PROFIT_1 is not None
    assert ExitReason.TAKE_PROFIT_2 is not None
    assert ExitReason.TAKE_PROFIT_TRAILING is not None
    assert ExitReason.STOP_LOSS_HALF is not None
    assert ExitReason.STOP_LOSS_CLEAR is not None
    assert ExitReason.TREND_CLEAR is not None

def test_lot_status_values():
    assert LotStatus.OPEN is not None
    assert LotStatus.CLOSED is not None

def test_signal_type_has_add_lot():
    assert SignalType.ADD_LOT is not None
    assert SignalType.STOP_ADD is not None
