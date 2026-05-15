# backend/risk/risk_manager.py
from backend import config


class RiskManager:
    def __init__(self):
        self._daily_pnl: float = 0.0
        self._halted: bool = False
        self._consec_loss_days: int = 0
        self._consec_profit_days: int = 0

    def record_pnl(self, pnl_yuan: float, gold_price: float) -> None:
        self._daily_pnl += pnl_yuan
        limit = config.T_POSITION_G * gold_price * config.DAILY_LOSS_LIMIT_RATE
        if self._daily_pnl <= -limit:
            self._halted = True

    def can_trade(self) -> bool:
        return not self._halted

    def reset_daily(self) -> None:
        if self._daily_pnl < 0:
            self._consec_loss_days += 1
            self._consec_profit_days = 0
        else:
            self._consec_profit_days += 1
            if self._consec_profit_days >= config.CONSECUTIVE_LOSS_DAYS:
                self._consec_loss_days = 0
        self._daily_pnl = 0.0
        self._halted = False

    def unit_buy_g(self) -> float:
        if self._consec_loss_days >= config.CONSECUTIVE_LOSS_DAYS:
            return config.REDUCED_UNIT_BUY_G
        return config.UNIT_BUY_G

    @property
    def daily_pnl(self) -> float:
        return self._daily_pnl
