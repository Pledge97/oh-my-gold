# data_service/main.py
# 独立的 tick 采集服务，与量化引擎解耦，共享同一个 SQLite 数据库。
# 启动：uvicorn main:app --port 8001
from contextlib import asynccontextmanager
from datetime import datetime, time as dtime, timedelta, date
from pathlib import Path
import sqlite3
import time

import httpx
import chinese_calendar
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, Query

from kline import build_kline

# ── 配置 ──────────────────────────────────────────────────────
DB_PATH = str(Path(__file__).parent.parent / "data" / "gold.db")
JDJYGOLD_URL = "https://api.jdjygold.com/gw2/generic/jrm/h5/m/stdLatestPrice"
JDJYGOLD_SKU = "1961543816"
TICK_INTERVAL_SEC = 5


# ── 交易时间判断 ───────────────────────────────────────────────

def is_trading_time() -> bool:
    dt = datetime.now()
    weekday = dt.weekday()
    t = dt.time()

    if weekday == 6:
        return False

    if weekday == 5:
        in_session = t < dtime(2, 30)
    elif weekday == 0:
        in_session = t >= dtime(9, 0)
    else:
        in_session = True

    if not in_session:
        return False

    trade_date = (dt - timedelta(days=1)).date() if t < dtime(2, 30) else dt.date()
    return chinese_calendar.is_workday(trade_date)


# ── 数据库 ────────────────────────────────────────────────────

def get_conn() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── 采集任务 ──────────────────────────────────────────────────

async def tick_job() -> None:
    if not is_trading_time():
        return

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(JDJYGOLD_URL, params={"productSku": JDJYGOLD_SKU})
        d = r.json()
        if not d.get("success"):
            return
        price = float(d["resultData"]["datas"]["price"])
    except Exception:
        print("[data_service] tick 采集失败")
        return

    ts = int(time.time() * 1000)
    with get_conn() as conn:
        conn.execute("INSERT INTO prices (ts, price) VALUES (?, ?)", (ts, price))


# ── 应用生命周期 ──────────────────────────────────────────────

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        tick_job,
        "interval",
        seconds=TICK_INTERVAL_SEC,
        next_run_time=datetime.now(),
    )
    scheduler.start()
    print(f"[data_service] 采集服务已启动，每 {TICK_INTERVAL_SEC} 秒写入一次 tick")
    yield
    scheduler.shutdown()


app = FastAPI(title="Gold Data Service", lifespan=lifespan)


# ── 接口 ──────────────────────────────────────────────────────

@app.get("/kline/minute")
def kline_minute(
    start: int = Query(..., description="开始时间（毫秒时间戳）"),
    end: int = Query(..., description="结束时间（毫秒时间戳）"),
    period: int = Query(5, ge=1, le=1440, description="K 线周期（分钟数）"),
):
    """
    返回指定时间段的分钟级 K 线数据。
    date 字段为毫秒时间戳，其余列名与 akshare spot_hist_sge 一致。
    """
    if start >= end:
        raise HTTPException(status_code=400, detail="start 必须小于 end")

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ts, price FROM prices WHERE ts >= ? AND ts <= ? ORDER BY ts ASC",
            (start, end),
        ).fetchall()

    if not rows:
        return []

    ticks = [{"ts": r["ts"], "price": r["price"]} for r in rows]
    df = build_kline(ticks, period_sec=period * 60)

    # ts -> date，与 akshare 列名对齐（date 字段用毫秒时间戳）
    df = df.rename(columns={"ts": "date"})
    return df.to_dict(orient="records")


@app.get("/kline/daily")
def kline_daily(
    start: str = Query(..., description="开始日期（YYYY-MM-DD）"),
    end: str = Query(..., description="结束日期（YYYY-MM-DD）"),
):
    """
    返回指定日期范围的日 K 数据，格式与 akshare spot_hist_sge 完全一致。
    """
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date, open, high, low, close, volume "
            "FROM daily_prices WHERE date >= ? AND date <= ? ORDER BY date ASC",
            (start, end),
        ).fetchall()

    return [dict(r) for r in rows]


@app.get("/health")
def health():
    """健康检查，返回最新一条 tick 的时间和价格"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT ts, price FROM prices ORDER BY ts DESC LIMIT 1"
        ).fetchone()
    if not row:
        return {"status": "ok", "latest_tick": None}
    return {
        "status": "ok",
        "latest_tick": {
            "ts": row["ts"],
            "price": row["price"],
            "time": datetime.fromtimestamp(row["ts"] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
        },
    }
