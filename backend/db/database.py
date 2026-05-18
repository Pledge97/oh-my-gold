import sqlite3
from pathlib import Path
from typing import Optional

from backend.db import models

# 默认数据库路径（生产环境）
DB_PATH = Path(__file__).parent.parent.parent / "data" / "gold.db"


def get_conn(db_path: Optional[str] = None) -> sqlite3.Connection:
    """获取数据库连接。db_path 为 None 时使用默认路径。"""
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None):
    """初始化数据库，创建所有表。db_path 为 None 时使用默认路径（生产环境）。"""
    conn = get_conn(db_path)
    try:
        for sql in [
            models.CREATE_DAILY_PRICES,
            models.CREATE_PRICES,
            models.CREATE_SIGNALS,
            models.CREATE_POSITIONS,
            models.CREATE_POSITION_LOTS,
            models.CREATE_CIRCUIT_BREAKER_LOGS,
        ]:
            conn.execute(sql)
        conn.executescript(models.CREATE_INDEXES)
        conn.commit()
    finally:
        conn.close()
