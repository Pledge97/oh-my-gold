# backend/main.py
import time
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, WebSocket
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.db.database import init_db
from backend.data.fetch_history import fetch_and_store
from backend.strategy.engine import StrategyEngine
from backend.api.routes import router
from backend.api.websocket import ws_endpoint, broadcast
from backend.core.scheduler import tick_job, _init_tick_cache
from backend import config

engine = StrategyEngine()
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    fetch_and_store()
    _init_tick_cache()  # 从数据库加载历史 tick 到内存缓存
    scheduler.add_job(
        tick_job,
        "interval",
        seconds=config.TICK_INTERVAL_SEC,
        next_run_time=datetime.now(),  # 启动后立即执行第一次
        kwargs={"engine": engine, "broadcast_fn": broadcast},
    )
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def log_request_time(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    elapsed = time.time() - t0
    print(f"[api] {request.method} {request.url.path}?{request.url.query} 耗时 {elapsed:.3f}s")
    return response


app.include_router(router)


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await ws_endpoint(websocket)
