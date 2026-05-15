# backend/db/models.py
# 所有建表 SQL 常量，集中管理数据库 schema

CREATE_DAILY_PRICES = """
CREATE TABLE IF NOT EXISTS daily_prices (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    date   TEXT NOT NULL UNIQUE,
    open   REAL NOT NULL,
    high   REAL NOT NULL,
    low    REAL NOT NULL,
    close  REAL NOT NULL,
    volume REAL
);
"""

CREATE_PRICES = """
CREATE TABLE IF NOT EXISTS prices (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    ts    INTEGER NOT NULL,
    price REAL NOT NULL
);
"""

CREATE_PRICES_JD = """
CREATE TABLE IF NOT EXISTS prices_jd (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    ts    INTEGER NOT NULL UNIQUE,
    price REAL NOT NULL
);
"""

CREATE_SIGNALS = """
CREATE TABLE IF NOT EXISTS signals (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       INTEGER NOT NULL,
    type     TEXT NOT NULL,
    mode     TEXT NOT NULL,
    price    REAL NOT NULL,
    amount_g REAL NOT NULL,
    reason   TEXT
);
"""

# positions 表保持与 position.py 兼容的原始 schema
# V2 新增字段通过 position_lots 表管理批次明细
CREATE_POSITIONS = """
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
"""

# V2 批次明细表：记录每一笔买入/卖出的具体信息
CREATE_POSITION_LOTS = """
CREATE TABLE IF NOT EXISTS position_lots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id     INTEGER NOT NULL,
    lot_index    INTEGER NOT NULL,
    open_ts      INTEGER NOT NULL,
    open_price   REAL NOT NULL,
    amount_g     REAL NOT NULL,
    status       TEXT NOT NULL DEFAULT 'OPEN',
    close_ts     INTEGER,
    close_price  REAL,
    close_reason TEXT
);
"""

CREATE_CIRCUIT_BREAKER_LOGS = """
CREATE TABLE IF NOT EXISTS circuit_breaker_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_ts    INTEGER NOT NULL,
    level         INTEGER NOT NULL,
    reason        TEXT NOT NULL,
    trigger_value REAL,
    resume_ts     INTEGER
);
"""

# 索引：加速按时间戳查询
CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_prices_ts ON prices(ts);
CREATE INDEX IF NOT EXISTS idx_prices_jd_ts ON prices_jd(ts);
"""
