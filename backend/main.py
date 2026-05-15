# backend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.db.database import init_db
from backend.data.fetch_history import fetch_and_store
from backend.strategy.engine import StrategyEngine
from backend.api.routes import router
from backend.api.websocket import ws_endpoint, broadcast
from backend.core.scheduler import tick_job
from backend import config

engine = StrategyEngine()
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    fetch_and_store()
    scheduler.add_job(
        tick_job,
        "interval",
        seconds=config.TICK_INTERVAL_SEC,
        kwargs={"engine": engine, "broadcast_fn": broadcast},
    )
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
app.include_router(router)


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await ws_endpoint(websocket)
