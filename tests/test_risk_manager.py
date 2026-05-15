# tests/test_risk_manager.py
import pytest
from backend.risk.risk_manager import RiskManager


def test_can_trade_initially():
    rm = RiskManager()
    assert rm.can_trade()


def test_halted_after_daily_loss_limit():
    rm = RiskManager()
    # T仓100g × 1000元/g × 3% = 3000元
    rm.record_pnl(-3001.0, gold_price=1000.0)
    assert not rm.can_trade()


def test_reset_resumes_trading():
    rm = RiskManager()
    rm.record_pnl(-3001.0, gold_price=1000.0)
    rm.reset_daily()
    assert rm.can_trade()


def test_unit_buy_reduced_after_consecutive_losses():
    rm = RiskManager()
    for _ in range(3):
        rm.record_pnl(-100.0, gold_price=1000.0)
        rm.reset_daily()
    assert rm.unit_buy_g() == 10.0


def test_unit_buy_restored_after_recovery():
    rm = RiskManager()
    for _ in range(3):
        rm.record_pnl(-100.0, gold_price=1000.0)
        rm.reset_daily()
    for _ in range(3):
        rm.record_pnl(100.0, gold_price=1000.0)
        rm.reset_daily()
    assert rm.unit_buy_g() == 20.0
