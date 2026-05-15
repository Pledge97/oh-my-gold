# backend/risk/position.py
import time
from dataclasses import dataclass, field
from backend.db.database import get_conn
from backend.core.enums import CloseType
from backend import config


@dataclass
class Position:
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
        return (current_price - self.open_price) / self.open_price

    def can_add(self) -> bool:
        return self.add_count < config.MAX_ADD_COUNT


class PositionManager:
    def open(self, price: float, amount_g: float) -> Position:
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
        ts = int(time.time() * 1000)
        fee = price * pos.amount_g * config.SELL_FEE_RATE
        pnl_yuan = (price - pos.open_price) * pos.amount_g - fee
        pnl_g = pnl_yuan / price
        with get_conn() as conn:
            conn.execute(
                """UPDATE positions SET status='CLOSED', close_ts=?, close_price=?,
                   close_type=?, pnl_yuan=?, pnl_g=? WHERE id=?""",
                (ts, price, close_type.value, pnl_yuan, pnl_g, pos.id),
            )
        return {"pnl_yuan": pnl_yuan, "pnl_g": pnl_g}

    def load_open(self) -> list[Position]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT id, open_ts, open_price, amount_g, add_count FROM positions WHERE status='OPEN'"
            ).fetchall()
        return [Position(id=r["id"], open_ts=r["open_ts"], open_price=r["open_price"],
                         amount_g=r["amount_g"], add_count=r["add_count"]) for r in rows]


# ── V2 组合仓位管理 ────────────────────────────────────────

from typing import List, Optional
from backend.core.enums import LotStatus


@dataclass
class Lot:
    """单批次买入明细"""
    lot_index: int                      # 批次序号：1/2/3
    open_price: float                   # 买入价格（元/g）
    amount_g: float                     # 买入克数
    open_ts: int                        # 买入时间（毫秒时间戳）
    status: LotStatus = LotStatus.OPEN
    close_ts: Optional[int] = None
    close_price: Optional[float] = None
    close_reason: Optional[str] = None


class PortfolioPosition:
    """
    T仓组合持仓管理（V2）。
    一轮交易 = 从第一笔买入到全部平仓。
    所有止盈/止损以组合整体盈亏率为基准，不对单笔单独止损。
    """

    def __init__(self, round_id: int):
        self.round_id = round_id        # 关联 positions.id
        self.lots: List[Lot] = []
        self.tp1_done: bool = False     # 第1次止盈是否已执行
        self.tp2_done: bool = False     # 第2次止盈是否已执行
        self._total_amount_g: float = 0.0
        self._total_cost: float = 0.0   # 总成本 = Σ(买入价 × 买入量)

    @property
    def total_amount_g(self) -> float:
        return self._total_amount_g

    @property
    def total_cost(self) -> float:
        return self._total_cost

    @property
    def avg_cost(self) -> float:
        """加权平均成本价（元/g）"""
        if self._total_amount_g == 0:
            return 0.0
        return self._total_cost / self._total_amount_g

    def is_empty(self) -> bool:
        return self._total_amount_g == 0.0

    def pnl_pct(self, current_price: float) -> float:
        """T仓整体浮盈浮亏率，扣除卖出手续费后的净盈亏率"""
        if self._total_cost == 0:
            return 0.0
        from backend import config
        market_value = current_price * self._total_amount_g
        fee = market_value * config.SELL_FEE_RATE
        return (market_value - fee - self._total_cost) / self._total_cost

    def add_lot(self, lot_index: int, price: float, amount_g: float, ts: int) -> Lot:
        """买入一批，返回 Lot 对象（调用方负责写库）"""
        lot = Lot(lot_index=lot_index, open_price=price, amount_g=amount_g, open_ts=ts)
        self.lots.append(lot)
        self._total_amount_g += amount_g
        self._total_cost += price * amount_g
        return lot

    @property
    def lot_count(self) -> int:
        """当前未平仓批次数"""
        return sum(1 for lot in self.lots if lot.status == LotStatus.OPEN)

    def reduce(self, ratio: float, close_price: float, ts: int) -> float:
        """
        按比例减仓，返回实际卖出克数。
        按平均成本比例减少总成本，不对单笔单独计算。
        """
        sold_g = self._total_amount_g * ratio
        self._total_cost -= self._total_cost * ratio
        self._total_amount_g -= sold_g
        self._total_amount_g = round(self._total_amount_g, 4)
        self._total_cost = round(self._total_cost, 4)
        return sold_g

    def clear(self, close_price: float, ts: int) -> float:
        """全部清仓，返回实际卖出克数"""
        sold_g = self._total_amount_g
        self._total_amount_g = 0.0
        self._total_cost = 0.0
        for lot in self.lots:
            if lot.status == LotStatus.OPEN:
                lot.status = LotStatus.CLOSED
                lot.close_ts = ts
                lot.close_price = close_price
        return sold_g

    def mark_tp1(self):
        """标记第1次止盈已执行"""
        self.tp1_done = True

    def mark_tp2(self):
        """标记第2次止盈已执行"""
        self.tp2_done = True
