# backend/data/fetcher_tick.py
import time
import httpx
import akshare as ak
from backend.db.database import get_conn
from backend import config


def fetch_akshare_price() -> float:
    df = ak.spot_quotation_sge()
    row = df[df["品种"] == config.AKSHARE_SYMBOL].iloc[0]
    return float(row["最新价"])


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
    # 主数据源：akshare AU9999
    try:
        price = fetch_akshare_price()
        store_tick(ts, price)
        # 同时静默采集 jdjygold（不影响主流程）
        try:
            jd_price = fetch_jdjygold_price()
            if jd_price:
                with get_conn() as conn:
                    conn.execute(
                        "INSERT INTO prices_jd (ts, price) VALUES (?, ?) ON CONFLICT DO NOTHING",
                        (ts, jd_price),
                    )
        except Exception:
            pass
        return price
    except Exception as e:
        print(f"[fetcher_tick] 采集失败: {e}")
        return None
