# backend/api/routes.py
from fastapi import APIRouter
from backend.db.database import get_conn

router = APIRouter(prefix="/api")


@router.get("/signals")
def get_signals(limit: int = 50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM signals ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/positions")
def get_positions(status: str = "OPEN"):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM positions WHERE status=? ORDER BY open_ts DESC", (status,)
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/performance")
def get_performance():
    with get_conn() as conn:
        t = conn.execute(
            "SELECT COUNT(*) cnt, SUM(pnl_yuan) total, "
            "SUM(CASE WHEN pnl_yuan>0 THEN 1 ELSE 0 END) wins "
            "FROM positions WHERE status='CLOSED'"
        ).fetchone()
        aw = conn.execute(
            "SELECT AVG(pnl_yuan) v FROM positions WHERE status='CLOSED' AND pnl_yuan>0"
        ).fetchone()
        al = conn.execute(
            "SELECT AVG(pnl_yuan) v FROM positions WHERE status='CLOSED' AND pnl_yuan<=0"
        ).fetchone()
    cnt = t["cnt"] or 0
    wins = t["wins"] or 0
    avg_w = aw["v"] or 0.0
    avg_l = al["v"] or 0.0
    return {
        "total_trades": cnt,
        "total_pnl_yuan": round(t["total"] or 0.0, 2),
        "win_rate": round(wins / cnt, 4) if cnt else 0.0,
        "avg_win_yuan": round(avg_w, 2),
        "avg_loss_yuan": round(avg_l, 2),
        "profit_loss_ratio": round(abs(avg_w / avg_l), 2) if avg_l else 0.0,
    }


@router.get("/prices/daily")
def get_daily_prices(days: int = 30):
    with get_conn() as conn:
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
