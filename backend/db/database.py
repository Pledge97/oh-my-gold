import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "gold.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS daily_prices (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                date   TEXT NOT NULL UNIQUE,
                open   REAL NOT NULL,
                high   REAL NOT NULL,
                low    REAL NOT NULL,
                close  REAL NOT NULL,
                volume REAL
            );

            CREATE TABLE IF NOT EXISTS prices (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                ts     INTEGER NOT NULL,
                price  REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_prices_ts ON prices(ts);

            CREATE TABLE IF NOT EXISTS signals (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                ts         INTEGER NOT NULL,
                type       TEXT NOT NULL,
                mode       TEXT NOT NULL,
                price      REAL NOT NULL,
                amount_g   REAL NOT NULL,
                reason     TEXT
            );

            CREATE TABLE IF NOT EXISTS positions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                open_ts     INTEGER NOT NULL,
                open_price  REAL NOT NULL,
                amount_g    REAL NOT NULL,
                add_count   INTEGER DEFAULT 0,
                status      TEXT NOT NULL DEFAULT 'OPEN',
                close_ts    INTEGER,
                close_price REAL,
                close_type  TEXT,
                pnl_yuan    REAL,
                pnl_g       REAL
            );

            CREATE TABLE IF NOT EXISTS circuit_breaker_logs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_ts    INTEGER NOT NULL,
                level         INTEGER NOT NULL,
                reason        TEXT NOT NULL,
                trigger_value REAL,
                resume_ts     INTEGER
            );

            CREATE TABLE IF NOT EXISTS prices_jd (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                ts    INTEGER NOT NULL UNIQUE,
                price REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_prices_jd_ts ON prices_jd(ts);
        """)
