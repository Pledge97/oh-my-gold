# backend/db/models.py
# 所有建表 SQL 常量，集中管理数据库 schema

CREATE_DAILY_PRICES = """
CREATE TABLE IF NOT EXISTS daily_prices (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    date   TEXT NOT NULL UNIQUE,  -- 日期（YYYY-MM-DD），来自 akshare AU9999
    open   REAL NOT NULL,         -- 开盘价（元/g）
    high   REAL NOT NULL,         -- 最高价（元/g）
    low    REAL NOT NULL,         -- 最低价（元/g）
    close  REAL NOT NULL,         -- 收盘价（元/g）
    volume REAL                   -- 成交量（可为空）
);
"""

CREATE_PRICES = """
CREATE TABLE IF NOT EXISTS prices (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    ts    INTEGER NOT NULL,  -- 采集时间（毫秒时间戳），来自 jdjygold
    price REAL NOT NULL      -- 积存金实时价格（元/g）
);
"""

CREATE_SIGNALS = """
CREATE TABLE IF NOT EXISTS signals (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       INTEGER NOT NULL,  -- 信号触发时间（毫秒时间戳）
    type     TEXT NOT NULL,     -- 信号类型（BUY/ADD_LOT/TAKE_PROFIT_1/TAKE_PROFIT_2/TAKE_PROFIT_TRAILING/STOP_LOSS_HALF/STOP_LOSS_CLEAR/TREND_CLEAR）
    mode     TEXT NOT NULL,     -- 市场状态（OSCILLATION/TREND_UP/TREND_DOWN/TREND_DECAY）
    price    REAL NOT NULL,     -- 触发时的金价（元/g）
    amount_g REAL NOT NULL,     -- 本次操作克数（g）
    reason   TEXT,              -- 触发原因描述
    pnl_yuan REAL               -- 本次卖出实现盈亏（元，仅卖出信号填写）
);
"""

# V3 底仓表：手动建仓的底仓记录，独立于 T仓信号流
CREATE_BASE_HOLDINGS = """
CREATE TABLE IF NOT EXISTS base_holdings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    open_ts     INTEGER NOT NULL,              -- 建仓时间（毫秒时间戳）
    open_price  REAL NOT NULL,                 -- 买入价格（元/g）
    amount_g    REAL NOT NULL,                 -- 持仓克数（g）
    status      TEXT NOT NULL DEFAULT 'OPEN',  -- 持仓状态（OPEN/CLOSED）
    close_ts    INTEGER,                       -- 平仓时间（毫秒时间戳，NULL 表示未平仓）
    close_price REAL,                          -- 平仓价格（元/g，NULL 表示未平仓）
    pnl_yuan    REAL                           -- 实现盈亏（元，NULL 表示未平仓）
);
"""

CREATE_CIRCUIT_BREAKER_LOGS = """
CREATE TABLE IF NOT EXISTS circuit_breaker_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_ts    INTEGER NOT NULL,  -- 熔断触发时间（毫秒时间戳）
    level         INTEGER NOT NULL,  -- 熔断级别（1=价格异常波动 / 2=ATR飙升 / 3=连续止损）
    reason        TEXT NOT NULL,     -- 触发原因描述
    trigger_value REAL,              -- 触发时的指标值（如价格变动幅度、ATR倍数）
    resume_ts     INTEGER            -- 熔断解除时间（毫秒时间戳，NULL 表示尚未解除）
);
"""

# 索引：加速常用查询字段的检索
CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_prices_ts ON prices(ts);
CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(ts);
CREATE INDEX IF NOT EXISTS idx_signals_type ON signals(type);
CREATE INDEX IF NOT EXISTS idx_base_holdings_status ON base_holdings(status);
"""
