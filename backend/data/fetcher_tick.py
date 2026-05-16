# backend/data/fetcher_tick.py
# 只负责拉取实时价格驱动策略引擎，tick 写库由 data_service 负责。
import httpx
from backend import config


def run_once() -> float | None:
    """拉取 jdjygold 最新价格，返回 float 或 None（失败时）。"""
    try:
        resp = httpx.get(
            config.JDJYGOLD_URL,
            params={"productSku": config.JDJYGOLD_SKU},
            timeout=5,
        )
        data = resp.json()
        if data.get("success"):
            return float(data["resultData"]["datas"]["price"])
    except Exception as e:
        print(f"[fetcher_tick] 采集失败: {e}")
    return None
