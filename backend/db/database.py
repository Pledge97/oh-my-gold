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


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    """如果旧库缺少字段，则执行 ALTER TABLE 补齐，保证迁移幂等。

    Args:
        conn:   已打开的数据库连接（row_factory 已设置为 sqlite3.Row）
        table:  目标表名
        column: 待检查的列名
        ddl:    补齐该列所需的 ALTER TABLE 语句
    """
    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(ddl)


def init_db(db_path: Optional[str] = None):
    """初始化 V3 数据库，创建所有表并补齐旧库缺失字段。

    V3 变更：
    - 新增 base_holdings 表（手动底仓）
    - signals 表新增 pnl_yuan 列（卖出实现盈亏）
    - 不再创建 positions / position_lots 表（T仓状态改由 signals 推导）

    Args:
        db_path: 数据库文件路径；为 None 时使用默认生产路径。
    """
    conn = get_conn(db_path)
    try:
        # V3 表集合：不包含已废弃的 positions / position_lots
        for sql in [
            models.CREATE_DAILY_PRICES,
            models.CREATE_PRICES,
            models.CREATE_SIGNALS,
            models.CREATE_BASE_HOLDINGS,
            models.CREATE_CIRCUIT_BREAKER_LOGS,
        ]:
            conn.execute(sql)
        conn.executescript(models.CREATE_INDEXES)
        # 对已存在的旧库补齐 V3 新增字段（幂等）
        _ensure_column(conn, "signals", "pnl_yuan", "ALTER TABLE signals ADD COLUMN pnl_yuan REAL")
        conn.commit()
    finally:
        conn.close()
