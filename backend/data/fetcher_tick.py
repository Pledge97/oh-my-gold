# backend/data/fetcher_tick.py
import time
import httpx
from backend.db.database import get_conn
from backend import config


def fetch_jdjygold_price() -> float | None:
    try:
        resp = httpx.get(
            config.JDJYGOLD_URL,
            params={"productSku": config.JDJYGOLD_SKU},
            timeout=5,
        )
        data = resp.json()
        if data.get("success"):
            return float(data["resultData"]["datas"]["price"])
    except Exception:
        pass
    return None


def store_tick(ts: int, price: float) -> None:
    with get_conn() as conn:
        conn.execute("INSERT INTO prices (ts, price) VALUES (?, ?)", (ts, price))


def run_once() -> float | None:
    ts = int(time.time() * 1000)
    try:
        price = fetch_jdjygold_price()
        if price is None:
            print("[fetcher_tick] jdjygold 返回空")
            return None
        store_tick(ts, price)
        return price
    except Exception as e:
        print(f"[fetcher_tick] 采集失败: {e}")
        return None
