# backend/api/routes.py
from fastapi import APIRouter
from pydantic import BaseModel
from backend.db.database import get_conn
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


@router.get("/positions")
def get_positions(status: str = "OPEN", source: str = "all"):
    with get_conn() as conn:
        if source == "manual":
            # 手动建仓：positions 表中没有对应 position_lots 记录的条目
            rows = conn.execute(
                "SELECT p.* FROM positions p "
                "WHERE p.status=? AND NOT EXISTS "
                "(SELECT 1 FROM position_lots l WHERE l.round_id=p.id) "
                "ORDER BY p.open_ts DESC",
                (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM positions WHERE status=? ORDER BY open_ts DESC", (status,)
            ).fetchall()
    return [dict(r) for r in rows]


class ManualPositionIn(BaseModel):
    amount_g: float
    open_price: float
    open_date: str  # YYYY-MM-DD


@router.post("/positions")
def create_position(body: ManualPositionIn):
    dt = datetime.strptime(body.open_date, "%Y-%m-%d")
    ts = int(dt.timestamp() * 1000)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO positions (open_ts, open_price, amount_g, status) VALUES (?, ?, ?, 'OPEN')",
            (ts, body.open_price, body.amount_g),
        )
        pos_id = cur.lastrowid
    return {"id": pos_id, "open_ts": ts, "open_price": body.open_price,
            "amount_g": body.amount_g, "status": "OPEN"}


@router.get("/performance")
def get_performance():
    sell_types = (
        'TAKE_PROFIT', 'TAKE_PROFIT_1', 'TAKE_PROFIT_2', 'TAKE_PROFIT_TRAILING',
        'STOP_LOSS', 'STOP_LOSS_HALF', 'STOP_LOSS_CLEAR', 'TREND_CLEAR'
    )
    placeholders = ','.join('?' * len(sell_types))

    with get_conn() as conn:
        # 总交易笔数：signals 表中卖出类型的信号数量
        cnt_row = conn.execute(
            f"SELECT COUNT(*) cnt FROM signals WHERE type IN ({placeholders})",
            sell_types
        ).fetchone()

        # 量化 T仓盈亏：有对应 position_lots 记录的 positions
        quant = conn.execute(
            "SELECT COUNT(*) cnt, SUM(p.pnl_yuan) total, "
            "SUM(CASE WHEN p.pnl_yuan>0 THEN 1 ELSE 0 END) wins "
            "FROM positions p WHERE p.status='CLOSED' "
            "AND EXISTS (SELECT 1 FROM position_lots l WHERE l.round_id=p.id)"
        ).fetchone()
        aw = conn.execute(
            "SELECT AVG(p.pnl_yuan) v FROM positions p WHERE p.status='CLOSED' AND p.pnl_yuan>0 "
            "AND EXISTS (SELECT 1 FROM position_lots l WHERE l.round_id=p.id)"
        ).fetchone()
        al = conn.execute(
            "SELECT AVG(p.pnl_yuan) v FROM positions p WHERE p.status='CLOSED' AND p.pnl_yuan<=0 "
            "AND EXISTS (SELECT 1 FROM position_lots l WHERE l.round_id=p.id)"
        ).fetchone()

        # 累计盈亏：所有已平仓（量化 + 手动底仓）
        total_pnl_row = conn.execute(
            "SELECT SUM(pnl_yuan) total FROM positions WHERE status='CLOSED'"
        ).fetchone()

    cnt = cnt_row["cnt"] or 0
    rounds = quant["cnt"] or 0
    wins = quant["wins"] or 0
    avg_w = aw["v"] or 0.0
    avg_l = al["v"] or 0.0
    return {
        "total_trades": cnt,
        "total_pnl_yuan": round(quant["total"] or 0.0, 2),       # 量化 T仓盈亏
        "cumulative_pnl_yuan": round(total_pnl_row["total"] or 0.0, 2),  # 全部累计盈亏
        "win_rate": round(wins / rounds, 4) if rounds else 0.0,
        "avg_win_yuan": round(avg_w, 2),
        "avg_loss_yuan": round(avg_l, 2),
        "profit_loss_ratio": round(abs(avg_w / avg_l), 2) if avg_l else 0.0,
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


class ClosePositionIn(BaseModel):
    close_price: float
    close_date: str  # YYYY-MM-DD HH:MM


@router.post("/positions/{pos_id}/close")
def close_position(pos_id: int, body: ClosePositionIn):
    dt = datetime.strptime(body.close_date, "%Y-%m-%d %H:%M")
    close_ts = int(dt.timestamp() * 1000)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT open_price, amount_g FROM positions WHERE id=? AND status='OPEN'",
            (pos_id,)
        ).fetchone()
        if not row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="持仓不存在或已平仓")
        fee = body.close_price * row["amount_g"] * 0.004
        pnl_yuan = (body.close_price - row["open_price"]) * row["amount_g"] - fee
        conn.execute(
            """UPDATE positions SET status='CLOSED', close_ts=?, close_price=?,
               close_type='MANUAL', pnl_yuan=? WHERE id=?""",
            (close_ts, body.close_price, round(pnl_yuan, 2), pos_id)
        )
    return {"id": pos_id, "pnl_yuan": round(pnl_yuan, 2), "status": "CLOSED"}


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
