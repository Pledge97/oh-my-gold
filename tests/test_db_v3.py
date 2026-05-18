import sqlite3
import tempfile
import os

from backend.db.database import init_db


def _new_db():
    """创建临时 SQLite 数据库文件，返回其路径。测试结束后由调用方负责删除。"""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return tmp.name


def test_base_holdings_table_exists_with_required_columns():
    """验证 V3 底仓表会在初始化时创建。"""
    db_path = _new_db()
    conn = None
    try:
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(base_holdings)").fetchall()}
        assert {
            "id", "open_ts", "open_price", "amount_g", "status",
            "close_ts", "close_price", "pnl_yuan",
        } <= cols
    finally:
        if conn:
            conn.close()
        os.unlink(db_path)


def test_signals_has_pnl_yuan_column():
    """验证 signals 支持记录每次卖出实现盈亏。"""
    db_path = _new_db()
    conn = None
    try:
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(signals)").fetchall()}
        assert "pnl_yuan" in cols
    finally:
        if conn:
            conn.close()
        os.unlink(db_path)


def test_v3_init_does_not_create_legacy_position_tables():
    """验证新库不再创建 V2 T 仓旧表。"""
    db_path = _new_db()
    conn = None
    try:
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert "positions" not in tables
        assert "position_lots" not in tables
    finally:
        if conn:
            conn.close()
        os.unlink(db_path)
