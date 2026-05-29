# backend/risk/circuit_breaker.py
import sqlite3
import time
from dataclasses import dataclass
from backend.db.database import get_conn
from backend import config
from backend.core.market_hours import CST
from backend.notifications.pushplus import send_circuit_breaker_notice
from datetime import datetime


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
        self._restore_from_db()

    @property
    def is_active(self) -> bool:
        if not self._state.active:
            return False
        if self._state.level in (1, 2, 3) and time.time() * 1000 >= self._state.resume_ts:
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
                               f"5秒涨跌幅={tick_pct:.3%}", tick_pct, price=price)
                return

        # 一级：5分钟涨跌幅
        if price_5m_ago > 0:
            pct_5m = abs(price - price_5m_ago) / price_5m_ago
            if pct_5m >= config.CB1_5MIN_PCT:
                self._activate(1, now_ms + config.CB1_5MIN_PAUSE_MIN * 60_000,
                               f"5分钟涨跌幅={pct_5m:.3%}", pct_5m, price=price)

    def check_atr(self, atr_current: float, atr_daily_mean: float, price: float | None = None) -> None:
        if self.is_active or atr_daily_mean <= 0:
            return
        if atr_current >= config.CB2_ATR_MULT * atr_daily_mean:
            resume_ts = self._long_pause_resume_ts()
            self._activate(2, resume_ts,
                           f"ATR={atr_current:.2f} 超过均值{config.CB2_ATR_MULT}倍",
                           atr_current / atr_daily_mean,
                           price=price)

    def on_stop_loss(self, price: float | None = None) -> None:
        self._daily_stop_count += 1
        if self._daily_stop_count >= config.CB3_DAILY_STOP_COUNT:
            self._activate(3, self._long_pause_resume_ts(),
                           f"单日止损{self._daily_stop_count}次", self._daily_stop_count, price=price)

    def reset_daily(self) -> None:
        self._daily_stop_count = 0

    def manual_resume(self) -> None:
        if self._state.level == 3:
            self._state = BreakerState()

    def _activate(self, level: int, resume_ts: int, reason: str, value: float,
                  price: float | None = None) -> None:
        self._state = BreakerState(active=True, level=level,
                                   resume_ts=resume_ts, reason=reason)
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO circuit_breaker_logs
                   (trigger_ts, level, reason, trigger_value, resume_ts)
                   VALUES (?, ?, ?, ?, ?)""",
                (int(time.time() * 1000), level, reason, value, resume_ts),
            )
        send_circuit_breaker_notice(level, price, reason)

    def _long_pause_resume_ts(self) -> int:
        """返回长暂停解除时间戳（毫秒）。"""
        return int(time.time() * 1000) + config.CB_LONG_PAUSE_HOURS * 60 * 60_000

    def _restore_from_db(self) -> None:
        """从数据库恢复当天止损次数和未到期熔断状态。"""
        try:
            with get_conn() as conn:
                self._restore_daily_stop_count(conn)
                self._restore_active_state(conn)
        except sqlite3.OperationalError:
            return

    def _restore_daily_stop_count(self, conn) -> None:
        """从当天止损信号恢复三级熔断计数。"""
        now_dt = datetime.fromtimestamp(time.time(), tz=CST)
        day_start = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        day_start_ts = int(day_start.timestamp() * 1000)
        row = conn.execute(
            "SELECT COUNT(*) cnt FROM signals "
            "WHERE ts >= ? AND type IN ('STOP_LOSS_HALF', 'STOP_LOSS_CLEAR')",
            (day_start_ts,),
        ).fetchone()
        self._daily_stop_count = int(row["cnt"] or 0)

    def _restore_active_state(self, conn) -> None:
        """从熔断日志恢复尚未到期的熔断状态。"""
        now_ms = int(time.time() * 1000)
        row = conn.execute(
            "SELECT level, reason, resume_ts FROM circuit_breaker_logs "
            "WHERE resume_ts > ? ORDER BY trigger_ts DESC LIMIT 1",
            (now_ms,),
        ).fetchone()
        if row is None:
            return
        self._state = BreakerState(
            active=True,
            level=int(row["level"]),
            resume_ts=int(row["resume_ts"]),
            reason=str(row["reason"]),
        )

    @property
    def state(self) -> BreakerState:
        return self._state
