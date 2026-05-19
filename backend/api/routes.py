# backend/api/routes.py
from fastapi import APIRouter
from pydantic import BaseModel
from backend.db.database import get_conn
from backend import config
from datetime import date, datetime
from typing import Optional

router = APIRouter(prefix="/api")


@router.get("/signals")
def get_signals(limit: int = 50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM signals ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


class BaseHoldingIn(BaseModel):
    """底仓建仓请求体。"""
    amount_g: float
    open_price: float
    open_date: str  # YYYY-MM-DD


class CloseBaseHoldingIn(BaseModel):
    """底仓平仓请求体。"""
    close_price: float
    close_date: str  # YYYY-MM-DD HH:MM


@router.get("/base_holdings")
def get_base_holdings(status: str = "OPEN"):
    """查询底仓列表。"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM base_holdings WHERE status=? ORDER BY open_ts DESC",
            (status,),
        ).fetchall()
    return [dict(row) for row in rows]


@router.post("/base_holdings")
def create_base_holding(body: BaseHoldingIn):
    """新建底仓记录。"""
    dt = datetime.strptime(body.open_date, "%Y-%m-%d")
    ts = int(dt.timestamp() * 1000)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO base_holdings (open_ts, open_price, amount_g, status) VALUES (?, ?, ?, 'OPEN')",
            (ts, body.open_price, body.amount_g),
        )
        pos_id = cur.lastrowid
    return {"id": pos_id, "open_ts": ts, "open_price": body.open_price,
            "amount_g": body.amount_g, "status": "OPEN"}


@router.post("/base_holdings/{pos_id}/close")
def close_base_holding(pos_id: int, body: CloseBaseHoldingIn):
    """平仓底仓，计算盈亏（扣除手续费）。"""
    dt = datetime.strptime(body.close_date, "%Y-%m-%d %H:%M")
    close_ts = int(dt.timestamp() * 1000)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT open_price, amount_g FROM base_holdings WHERE id=? AND status='OPEN'",
            (pos_id,)
        ).fetchone()
        if not row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="底仓不存在或已平仓")
        fee = body.close_price * row["amount_g"] * config.SELL_FEE_RATE
        pnl_yuan = (body.close_price - row["open_price"]) * row["amount_g"] - fee
        conn.execute(
            "UPDATE base_holdings SET status='CLOSED', close_ts=?, close_price=?, pnl_yuan=? WHERE id=?",
            (close_ts, body.close_price, round(pnl_yuan, 2), pos_id)
        )
    return {"id": pos_id, "pnl_yuan": round(pnl_yuan, 2), "status": "CLOSED"}


@router.get("/performance")
def get_performance():
    """绩效统计：T仓盈亏来自 signals，底仓盈亏来自 base_holdings。"""
    # 卖出类型信号枚举
    sell_types = (
        "TAKE_PROFIT_1", "TAKE_PROFIT_2", "TAKE_PROFIT_TRAILING",
        "STOP_LOSS_HALF", "STOP_LOSS_CLEAR", "TREND_CLEAR",
    )
    placeholders = ",".join("?" * len(sell_types))

    with get_conn() as conn:
        # 总交易笔数：signals 中卖出类型的信号数
        cnt_row = conn.execute(
            f"SELECT COUNT(*) cnt FROM signals WHERE type IN ({placeholders})",
            sell_types,
        ).fetchone()

        # T仓盈亏：signals 中卖出信号的 pnl_yuan 之和
        t_pnl_row = conn.execute(
            f"SELECT SUM(pnl_yuan) total FROM signals WHERE type IN ({placeholders})",
            sell_types,
        ).fetchone()

        # 底仓盈亏：base_holdings 中已平仓记录的 pnl_yuan 之和
        base_pnl_row = conn.execute(
            "SELECT SUM(pnl_yuan) total FROM base_holdings WHERE status='CLOSED'"
        ).fetchone()

        # 胜率：按轮次分组（Python 层计算）
        # 一轮 = 从第一次买入到全清仓（STOP_LOSS_CLEAR/TREND_CLEAR/TAKE_PROFIT_TRAILING）
        # 该轮所有卖出信号 pnl_yuan 之和 > 0 则为盈利轮次
        all_sells = conn.execute(
            f"SELECT ts, type, pnl_yuan FROM signals WHERE type IN ({placeholders}) ORDER BY ts ASC",
            sell_types,
        ).fetchall()

    # 触发全清仓的信号类型
    full_clear_types = {"STOP_LOSS_CLEAR", "TREND_CLEAR", "TAKE_PROFIT_TRAILING"}
    rounds_pnl: list[float] = []
    current_round_pnl: float = 0.0
    has_sells_in_round: bool = False

    for row in all_sells:
        pnl = row["pnl_yuan"] or 0.0
        current_round_pnl += pnl
        has_sells_in_round = True
        if row["type"] in full_clear_types:
            rounds_pnl.append(current_round_pnl)
            current_round_pnl = 0.0
            has_sells_in_round = False

    # 当前未完成轮次（有卖出但未全清仓）也计入
    if has_sells_in_round:
        rounds_pnl.append(current_round_pnl)

    total_rounds = len(rounds_pnl)
    wins = sum(1 for p in rounds_pnl if p > 0)
    t_pnl = t_pnl_row["total"] or 0.0
    base_pnl = base_pnl_row["total"] or 0.0

    return {
        "total_trades": cnt_row["cnt"] or 0,
        "total_pnl_yuan": round(t_pnl, 2),
        "cumulative_pnl_yuan": round(t_pnl + base_pnl, 2),
        "win_rate": round(wins / total_rounds, 4) if total_rounds else 0.0,
        "avg_win_yuan": 0.0,   # 暂不计算，前端未使用
        "avg_loss_yuan": 0.0,
        "profit_loss_ratio": 0.0,
    }


@router.get("/prices/tick")
def get_tick_prices(hours: int = 24):
    since_ms = int((datetime.now().timestamp() - hours * 3600) * 1000)
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ts, price FROM prices WHERE ts >= ? ORDER BY ts ASC",
            (since_ms,)
        ).fetchall()
        if not rows:
            rows = conn.execute(
                "SELECT ts, price FROM prices ORDER BY ts ASC"
            ).fetchall()
    return [{"ts": r["ts"], "price": r["price"]} for r in rows]


@router.get("/prices/latest")
def get_latest_price():
    """返回数据库中最新一条 tick 价格，用于页面初始化显示"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT price FROM prices ORDER BY ts DESC LIMIT 1"
        ).fetchone()
    return {"price": row["price"] if row else 0.0}


@router.get("/prices/daily")
def get_daily_prices(
    days: int = 30,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    with get_conn() as conn:
        if start_date or end_date:
            conditions = []
            params = []
            if start_date:
                conditions.append("date >= ?")
                params.append(start_date.isoformat())
            if end_date:
                conditions.append("date <= ?")
                params.append(end_date.isoformat())
            rows = conn.execute(
                "SELECT date, open, high, low, close FROM daily_prices "
                f"WHERE {' AND '.join(conditions)} ORDER BY date ASC",
                params,
            ).fetchall()
            return [dict(r) for r in rows]

        rows = conn.execute(
            "SELECT date, open, high, low, close FROM daily_prices "
            "ORDER BY date DESC LIMIT ?", (days,)
        ).fetchall()
        return list(reversed([dict(r) for r in rows]))


@router.get("/circuit-breaker")
def get_cb_status():
    with get_conn() as conn:
        logs = conn.execute(
            "SELECT * FROM circuit_breaker_logs ORDER BY trigger_ts DESC LIMIT 20"
        ).fetchall()
    return [dict(r) for r in logs]


@router.post("/circuit-breaker/resume")
def resume_cb():
    from backend.main import engine
    engine.cb.manual_resume()
    return {"status": "resumed"}
