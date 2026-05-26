from datetime import datetime, timedelta, timezone

import pytest

from backend.api.routes import get_tick_prices
from backend.db.database import init_db, get_conn

# 北京时间 UTC+8
CST = timezone(timedelta(hours=8))


def ts(dt_str: str) -> int:
    """将 'YYYY-MM-DD HH:MM' 转为毫秒时间戳（北京时间）。"""
    # 时间对象：用于生成稳定的测试时间戳。
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=CST)
    return int(dt.timestamp() * 1000)


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """每个用例使用独立测试库，避免污染本地开发数据。"""
    import backend.db.database as db_mod

    # 测试库路径：覆盖默认生产库路径。
    test_db_path = tmp_path / "test.db"
    monkeypatch.setattr(db_mod, "DB_PATH", test_db_path)
    init_db()


def insert_price(ts_ms: int, price: float) -> None:
    """插入一条测试 tick 价格。"""
    with get_conn() as conn:
        conn.execute("INSERT INTO prices (ts, price) VALUES (?, ?)", (ts_ms, price))
        conn.commit()


def test_tick_prices_use_latest_24_trading_hours():
    """验证 tick 接口按最新 tick 回溯 24 个开市小时，而不是自然时间。"""
    # 窗口外价格：早于周一 10:00 往前 24 个开市小时的起点。
    insert_price(ts("2025-05-16 02:00"), 1001.0)
    # 窗口内价格：周五 03:30 之后应被返回。
    insert_price(ts("2025-05-16 04:00"), 1002.0)
    # 休市价格：即使落在自然起止时间内，也不应被返回。
    insert_price(ts("2025-05-17 10:00"), 1099.0)
    # 窗口内价格：周一开市后的价格应被返回。
    insert_price(ts("2025-05-19 09:30"), 1003.0)
    # 最新价格：接口应以该 tick 作为截止时间。
    insert_price(ts("2025-05-19 10:00"), 1004.0)

    # 返回数据：只应包含累计 24 个开市小时窗口内的数据。
    rows = get_tick_prices(hours=24)

    assert [row["price"] for row in rows] == [1002.0, 1003.0, 1004.0]
