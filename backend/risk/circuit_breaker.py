# backend/risk/circuit_breaker.py
import time
from dataclasses import dataclass, field
from backend.db.database import get_conn
from backend import config


@dataclass
class BreakerState:
    active: bool = False
    level: int = 0
    resume_ts: int = 0
    reason: str = ""


class CircuitBreaker:
    def __init__(self):
        self._state = BreakerState()
        self._daily_stop_count: int = 0
        self._consec_stop_days: list[str] = []  # 日期字符串列表

    @property
    def is_active(self) -> bool:
        if not self._state.active:
            return False
        if self._state.level in (1, 2) and time.time() * 1000 >= self._state.resume_ts:
            self._state = BreakerState()
            return False
        return True

    def check_tick(self, price: float, prev_price: float, price_5m_ago: float) -> None:
        if self.is_active:
            return
        now_ms = int(time.time() * 1000)

        # 一级：5秒涨跌幅
        if prev_price > 0:
            tick_pct = abs(price - prev_price) / prev_price
            if tick_pct >= config.CB1_TICK_PCT:
                self._activate(1, now_ms + config.CB1_TICK_PAUSE_MIN * 60_000,
                               f"5秒涨跌幅={tick_pct:.3%}", tick_pct)
                return

        # 一级：5分钟涨跌幅
        if price_5m_ago > 0:
            pct_5m = abs(price - price_5m_ago) / price_5m_ago
            if pct_5m >= config.CB1_5MIN_PCT:
                self._activate(1, now_ms + config.CB1_5MIN_PAUSE_MIN * 60_000,
                               f"5分钟涨跌幅={pct_5m:.3%}", pct_5m)

    def check_atr(self, atr_current: float, atr_daily_mean: float) -> None:
        if self.is_active or atr_daily_mean <= 0:
            return
        if atr_current >= config.CB2_ATR_MULT * atr_daily_mean:
            # 暂停至次日00:00:00
            import datetime
            tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            resume_ts = int(tomorrow.timestamp() * 1000)
            self._activate(2, resume_ts,
                           f"ATR={atr_current:.2f} 超过均值{config.CB2_ATR_MULT}倍",
                           atr_current / atr_daily_mean)

    def on_stop_loss(self) -> None:
        self._daily_stop_count += 1
        if self._daily_stop_count >= config.CB3_DAILY_STOP_COUNT:
            # 暂停至次日
            import datetime
            tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            self._activate(3, int(tomorrow.timestamp() * 1000),
                           f"单日止损{self._daily_stop_count}次", self._daily_stop_count)

    def reset_daily(self) -> None:
        self._daily_stop_count = 0

    def manual_resume(self) -> None:
        if self._state.level == 3:
            self._state = BreakerState()

    def _activate(self, level: int, resume_ts: int, reason: str, value: float) -> None:
        self._state = BreakerState(active=True, level=level,
                                   resume_ts=resume_ts, reason=reason)
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO circuit_breaker_logs
                   (trigger_ts, level, reason, trigger_value, resume_ts)
                   VALUES (?, ?, ?, ?, ?)""",
                (int(time.time() * 1000), level, reason, value, resume_ts),
            )

    @property
    def state(self) -> BreakerState:
        return self._state
