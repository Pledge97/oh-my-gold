# tests/test_db_v2.py
import sqlite3
import tempfile
import os
from backend.db.database import init_db


def test_position_lots_table_exists():
    """验证 position_lots 表在初始化后存在"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = None
    try:
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='position_lots'"
        )
        assert cur.fetchone() is not None, "position_lots 表不存在"
    finally:
        if conn:
            conn.close()
        os.unlink(db_path)


def test_position_lots_columns():
    """验证 position_lots 表包含所有必要字段"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = None
    try:
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cur = conn.execute("PRAGMA table_info(position_lots)")
        cols = {row[1] for row in cur.fetchall()}
        assert {"id", "round_id", "lot_index", "open_ts", "open_price",
                "amount_g", "status", "close_ts", "close_price"} <= cols
    finally:
        if conn:
            conn.close()
        os.unlink(db_path)
