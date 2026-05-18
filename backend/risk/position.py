# backend/risk/position.py
import time
from dataclasses import dataclass
from backend.db.database import get_conn
from backend.core.enums import CloseType
from backend import config


@dataclass
class Position:
    """V1 单笔持仓记录（保留用于兼容）"""
    id: int
    open_ts: int
    open_price: float
    amount_g: float
    add_count: int = 0
    peak_price: float = 0.0

    def __post_init__(self):
        if self.peak_price == 0.0:
            self.peak_price = self.open_price

    def pnl_rate(self, current_price: float) -> float:
        """计算盈亏率"""
        return (current_price - self.open_price) / self.open_price

    def can_add(self) -> bool:
        """判断是否可以加仓"""
        return self.add_count < config.MAX_ADD_COUNT


class PositionManager:
    """V1 持仓管理器（保留用于兼容）"""

    def open(self, price: float, amount_g: float) -> Position:
        """开仓"""
        ts = int(time.time() * 1000)
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO positions (open_ts, open_price, amount_g, status) VALUES (?, ?, ?, 'OPEN')",
                (ts, price, amount_g),
            )
            pos_id = cur.lastrowid
        return Position(id=pos_id, open_ts=ts, open_price=price,
                        amount_g=amount_g, peak_price=price)

    def add(self, pos: Position, price: float, amount_g: float) -> None:
        """加仓"""
        new_total = pos.amount_g + amount_g
        new_avg = (pos.open_price * pos.amount_g + price * amount_g) / new_total
        pos.amount_g = new_total
        pos.open_price = new_avg
        pos.add_count += 1
        with get_conn() as conn:
            conn.execute(
                "UPDATE positions SET amount_g=?, open_price=?, add_count=? WHERE id=?",
                (new_total, new_avg, pos.add_count, pos.id),
            )

    def close(self, pos: Position, price: float, close_type: CloseType) -> dict:
        """平仓"""
        ts = int(time.time() * 1000)
        fee = price * pos.amount_g * config.SELL_FEE_RATE
        pnl_yuan = (price - pos.open_price) * pos.amount_g - fee
        with get_conn() as conn:
            conn.execute(
                """UPDATE positions SET status='CLOSED', close_ts=?, close_price=?,
                   close_type=?, pnl_yuan=? WHERE id=?""",
                (ts, price, close_type.value, pnl_yuan, pos.id),
            )
        return {"pnl_yuan": pnl_yuan}

    def load_open(self) -> list[Position]:
        """加载所有未平仓持仓"""
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT id, open_ts, open_price, amount_g, add_count FROM positions WHERE status='OPEN'"
            ).fetchall()
        return [Position(id=r["id"], open_ts=r["open_ts"], open_price=r["open_price"],
                         amount_g=r["amount_g"], add_count=r["add_count"]) for r in rows]

