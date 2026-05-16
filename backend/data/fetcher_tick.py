# backend/data/fetcher_tick.py
# 只负责拉取实时价格驱动策略引擎，tick 写库由 data_service 负责。
import httpx
from backend import config


async def run_once() -> float | None:
    """异步拉取 jdjygold 最新价格，不阻塞事件循环。"""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                config.JDJYGOLD_URL,
                params={"productSku": config.JDJYGOLD_SKU},
            )
        data = resp.json()
        if data.get("success"):
            return float(data["resultData"]["datas"]["price"])
    except Exception as e:
        print(f"[fetcher_tick] 采集失败: {e}")
    return None
