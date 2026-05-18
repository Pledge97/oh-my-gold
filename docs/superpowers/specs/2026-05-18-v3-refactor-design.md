# 黄金做T量化系统 V3 重构设计文档

**日期：** 2026-05-18
**版本：** v3.0
**背景：** V2 存在数据库设计缺陷——持仓表与批次表分离导致盈亏计算不完整、加仓逻辑卡死、内存状态重启丢失等问题。V3 以信号表为单一数据源，彻底简化数据层。

---

## 一、核心变更原则

- **信号表（signals）是 T仓的唯一数据源**：所有 T仓状态（持仓克数、均价、盈亏）从 signals 推导，不再单独维护持仓快照表
- **底仓表（base_holdings）专注底仓**：只存手动建仓的底仓数据，与 T仓完全解耦
- **删除 positions 和 position_lots 表**
- **加仓逻辑改为基于持仓量阈值**，不再依赖批次计数

---

## 二、数据库变更

### 2.1 删除表

| 表名 | 原用途 | 删除原因 |
|------|--------|---------|
| `positions` | T仓轮次汇总 + 底仓 | 混用导致区分逻辑复杂，T仓状态改从 signals 推导 |
| `position_lots` | T仓批次明细 | 删除 positions 后失去意义 |

### 2.2 新增表

```sql
CREATE TABLE IF NOT EXISTS base_holdings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    open_ts     INTEGER NOT NULL,           -- 买入时间（毫秒时间戳）
    open_price  REAL NOT NULL,              -- 买入价格（元/g）
    amount_g    REAL NOT NULL,              -- 持仓克数
    status      TEXT NOT NULL DEFAULT 'OPEN',  -- OPEN / CLOSED
    close_ts    INTEGER,                    -- 卖出时间（毫秒时间戳）
    close_price REAL,                       -- 卖出价格（元/g）
    pnl_yuan    REAL                        -- 卖出盈亏（元，已扣手续费）
);
```

### 2.3 修改表

`signals` 表新增 `pnl_yuan` 字段：

```sql
ALTER TABLE signals ADD COLUMN pnl_yuan REAL;
-- NULL 表示买入信号；有值表示卖出信号，记录本次卖出盈亏（已扣手续费）
```

### 2.4 保留不变的表

`daily_prices`、`prices`、`circuit_breaker_logs` 完全不变。

---

## 三、T仓状态推导逻辑

所有 T仓状态从 `signals` 表实时推导，不再存储快照。

### 3.1 当前轮次范围

**当前轮次** = 最近一条全清仓信号（`STOP_LOSS_CLEAR` / `TREND_CLEAR` / `TAKE_PROFIT_TRAILING`）之后的所有信号。如果没有全清仓信号，则所有信号都属于当前轮次。

```python
def get_current_round_signals(conn) -> list[dict]:
    """取当前轮次的所有信号（最后一次全清仓之后）"""
    full_clear_types = ('STOP_LOSS_CLEAR', 'TREND_CLEAR', 'TAKE_PROFIT_TRAILING')
    last_clear = conn.execute(
        "SELECT MAX(ts) ts FROM signals WHERE type IN (?,?,?)",
        full_clear_types
    ).fetchone()
    since_ts = last_clear['ts'] or 0
    return conn.execute(
        "SELECT * FROM signals WHERE ts > ? ORDER BY ts ASC", (since_ts,)
    ).fetchall()
```

### 3.2 持仓克数

```python
BUY_TYPES = ('BUY', 'ADD_LOT')
SELL_TYPES = ('TAKE_PROFIT_1', 'TAKE_PROFIT_2', 'TAKE_PROFIT_TRAILING',
              'STOP_LOSS_HALF', 'STOP_LOSS_CLEAR', 'TREND_CLEAR')

total_amount_g = sum(s['amount_g'] for s in signals if s['type'] in BUY_TYPES) \
               - sum(s['amount_g'] for s in signals if s['type'] in SELL_TYPES)
```

### 3.3 均价

```python
buy_cost = sum(s['price'] * s['amount_g'] for s in signals if s['type'] in BUY_TYPES)
buy_amount = sum(s['amount_g'] for s in signals if s['type'] in BUY_TYPES)
avg_cost = buy_cost / buy_amount if buy_amount > 0 else 0.0
```

### 3.4 已实现盈亏

```python
realized_pnl = sum(s['pnl_yuan'] for s in signals if s['pnl_yuan'] is not None)
```

### 3.5 浮盈亏（实时，前端计算）

```
浮盈亏 = 当前价 × 持仓克数 × (1 - SELL_FEE_RATE) - avg_cost × 持仓克数
```

---

## 四、T仓内存状态（PortfolioPosition）

去掉 `lots` 列表，只保留必要字段：

```python
class PortfolioPosition:
    round_counter: int      # 每次全清仓后递增，用于 WebSocket 推送区分轮次
    total_amount_g: float   # 当前持仓克数
    total_cost: float       # 当前持仓总成本（买入均价 × 持仓量）
    tp1_done: bool
    tp2_done: bool
    realized_pnl: float     # 本轮累计已实现盈亏
    _last_buy_price: float  # 上次买入价（用于加仓间距判断）
```

### 重启恢复（从 signals 表）

```python
def _load_portfolio_from_signals(conn) -> PortfolioPosition:
    signals = get_current_round_signals(conn)
    portfolio = PortfolioPosition()
    for s in signals:
        if s['type'] in BUY_TYPES:
            portfolio.total_cost += s['price'] * s['amount_g']
            portfolio.total_amount_g += s['amount_g']
            portfolio._last_buy_price = s['price']
        elif s['type'] in SELL_TYPES:
            ratio = s['amount_g'] / (portfolio.total_amount_g + s['amount_g'])
            portfolio.total_cost *= (1 - ratio)
            portfolio.total_amount_g -= s['amount_g']
            if s['pnl_yuan'] is not None:
                portfolio.realized_pnl += s['pnl_yuan']
        if s['type'] == 'TAKE_PROFIT_1':
            portfolio.tp1_done = True
        if s['type'] == 'TAKE_PROFIT_2':
            portfolio.tp2_done = True
    return portfolio
```

---

## 五、加仓逻辑重构

用 `total_amount_g` 替代 `lot_count` 判断加仓阶段。

| 当前持仓 | 初始建仓条件 | 加仓条件 | 买入量 | 目标持仓 |
|---------|------------|---------|--------|---------|
| 0g | 震荡：价格≤布林下轨 / 趋势：EMA20>EMA60且RSI≤40 | — | 50g | 50g |
| 0 < g < 50g | — | 价格跌 1×ATR | 补至50g | 50g |
| 50g ≤ g < 80g | — | 价格跌 1×ATR | 补至80g | 80g |
| 80g ≤ g < 100g | — | 价格跌 1×ATR | 补至100g | 100g |
| 100g | — | 满仓不加仓 | — | — |

止盈后持仓减少，可继续加仓补回，不再卡死。

---

## 六、卖出盈亏写入 signals

每次卖出时，在写入 signals 的同时计算并写入 `pnl_yuan`：

```python
def _calc_sell_pnl(sold_g: float, sell_price: float,
                   avg_cost: float, fee_rate: float) -> float:
    """本次卖出盈亏 = 卖出金额 - 成本 - 手续费"""
    revenue = sell_price * sold_g
    cost = avg_cost * sold_g
    fee = revenue * fee_rate
    return revenue - cost - fee
```

`avg_cost` 在 `reduce/clear` **之前**取值（此时成本尚未更新）。

---

## 七、前端变更

### 7.1 删除

- `frontend/src/components/PortfolioView.tsx`
- App.tsx 中 PortfolioView 的引用和布局

### 7.2 修改

**SignalPanel.tsx**：标题行下方新增 T仓状态栏

```
信号记录                    买入 997.04  止盈 1008.20  止损 978.92
───────────────────────────────────────────────────────────
持仓 50.0g  均价 ¥991.46  浮盈 +235.27元(+1.23%)
```

数据来源：WebSocket `portfolio` 字段（`total_amount_g`、`avg_cost`、`pnl_pct`、`pnl_yuan`）。

**PositionTable.tsx（底仓）**：
- API 改为 `/api/base_holdings`
- 去掉 source 过滤参数

**App.tsx**：右侧改回两栏（信号面板上半，底仓下半）

### 7.3 WebSocket portfolio 字段简化

去掉 `lots` 数组，保留：

```json
{
  "round_counter": 3,
  "total_amount_g": 50.0,
  "avg_cost": 991.46,
  "pnl_pct": 0.0123,
  "pnl_yuan": 56.34,
  "tp1_done": true,
  "tp2_done": false,
  "next_buy": 986.46,
  "next_tp": 1001.87,
  "next_stop": 966.97
}
```

---

## 八、API 变更

| 旧接口 | 新接口 | 变更 |
|--------|--------|------|
| `GET /api/positions?source=manual` | `GET /api/base_holdings` | 表名变更，去掉 source 参数 |
| `POST /api/positions` | `POST /api/base_holdings` | 同上 |
| `POST /api/positions/{id}/close` | `POST /api/base_holdings/{id}/close` | 同上 |
| `GET /api/performance` | 不变 | 数据源从 signals 表推导 |

---

## 九、性能统计变更

**总交易笔数**：`signals` 中卖出类型信号数（不变）

**T仓盈亏**：`SUM(pnl_yuan) FROM signals WHERE type IN (sell_types)`

**累计盈亏**：T仓盈亏 + `SUM(pnl_yuan) FROM base_holdings WHERE status='CLOSED'`

**胜率**：按每次卖出信号是否盈利统计（`pnl_yuan > 0` 的卖出信号数 / 总卖出信号数）

---

## 十、迁移策略（已完成）

迁移脚本已手动执行，现有数据状态：

1. ✅ `signals` 表新增 `pnl_yuan` 字段，历史卖出记录（id=18: 178.93元，id=19: 56.34元）已补写
2. ✅ `base_holdings` 表已创建，7条底仓 OPEN 记录 + 1条 CLOSED 记录已从 `positions` 迁移
3. ✅ 当前 T仓状态（signal id=20，996.44买入50g）可从 `signals` 表重建
4. 实施计划执行时直接删除 `positions` 和 `position_lots` 旧表
