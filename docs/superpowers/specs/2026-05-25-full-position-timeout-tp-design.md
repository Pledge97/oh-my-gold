# 满仓超时降低止盈门槛设计

## 背景

震荡行情波动较小时，策略满仓（100g）后价格可能在成本附近横盘，既涨不到 TP1 触发线（0.6%），也跌不到止损线（-2.5%），导致资金被套住数天无法解锁。

## 目标

满仓后累计交易时长超过 24 小时，将 TP1 止盈触发阈值从 0.6% 降低到 0.3%，让策略在小幅盈利时也能及时止盈离场。卖出比例（60%）和后续 TP2、追踪止盈逻辑保持不变。

## 设计

### 触发条件

- 持仓量达到 `T_MAX_AMOUNT_G`（100g）
- TP1 尚未执行（`tp1_done == False`）
- 自满仓起累计**交易时段内**时长 ≥ 24 小时（非交易时段暂停计时）

### 效果

| 状态 | TP1 触发阈值 | 卖出比例 |
|------|------------|---------|
| 正常 | 0.6% | 60% |
| 满仓超时 | 0.3% | 60% |

TP2（1.2%）、追踪止盈（EMA 跌破）逻辑不变。

---

## 组件改动

### 1. `backend/config.py`

新增两个常量：

```python
FULL_POSITION_TIMEOUT_HOURS: float = 24.0     # 满仓超时阈值（交易小时）
FULL_POSITION_TIMEOUT_TP1_PCT: float = 0.003  # 超时后降低的 TP1 止盈率（0.3%）
```

### 2. `backend/core/market_hours.py`

新增工具函数：

```python
def calc_trading_seconds(since_ts_ms: int, until_ts_ms: int, step_sec: int = 60) -> float
```

从 `since_ts_ms` 到 `until_ts_ms`，按 `step_sec` 步长采样，累计处于交易时段内的秒数。复用已有的 `is_trading_time`，不引入新依赖。

### 3. `backend/risk/portfolio.py` — `PortfolioPosition`

新增内存字段：

```python
full_since_ts: int | None = None  # 首次达到满仓的时间戳（毫秒），非交易时段不计入
```

`buy()` 方法：买入后若 `total_amount_g >= T_MAX_AMOUNT_G` 且 `full_since_ts is None`，记录当前 `ts`。

`sell()` 方法：卖出后若 `total_amount_g < T_MAX_AMOUNT_G`，清除 `full_since_ts = None`。

> `buy()` 和 `sell()` 需新增 `ts: int` 参数，engine 调用处同步传入 `ctx.ts`。

### 4. `backend/signals/sell_signal.py`

`check_sell_signal` 在计算 `tp1_pct` 之前，插入超时检查：

```python
if (
    not portfolio.tp1_done
    and portfolio.full_since_ts is not None
    and portfolio.total_amount_g >= config.T_MAX_AMOUNT_G
):
    trading_secs = calc_trading_seconds(portfolio.full_since_ts, current_ts_ms)
    if trading_secs >= config.FULL_POSITION_TIMEOUT_HOURS * 3600:
        tp1_pct = config.FULL_POSITION_TIMEOUT_TP1_PCT
```

`check_sell_signal` 需新增 `current_ts_ms: int` 参数，engine 调用处传入 `ctx.ts`。

### 5. `backend/risk/portfolio.py` — `load_portfolio_from_signals`

重启恢复逻辑：回放完成后，若 `total_amount_g >= T_MAX_AMOUNT_G`，将最后一笔 BUY/ADD_LOT 信号的 `ts` 赋值给 `full_since_ts`（保守估计，实际满仓时间不晚于此）。

---

## 影响范围

| 文件 | 改动类型 |
|------|---------|
| `backend/config.py` | 新增 2 个常量 |
| `backend/core/market_hours.py` | 新增 `calc_trading_seconds` 函数 |
| `backend/risk/portfolio.py` | `PortfolioPosition` 新增 `full_since_ts` 字段；`buy()`/`sell()` 新增 `ts` 参数；`load_portfolio_from_signals` 恢复逻辑 |
| `backend/signals/sell_signal.py` | `check_sell_signal` 新增 `current_ts_ms` 参数和超时分支 |
| `backend/strategy/engine.py` | 更新 `buy()`/`sell()`/`check_sell_signal` 调用处，传入 `ctx.ts` |

## 不变的部分

- 止损逻辑（`exit_signal.py`）不变
- 买入逻辑（`buy_signal.py`）不变
- TREND_UP 专属止盈阈值不变
- TP2、追踪止盈逻辑不变
- 非满仓状态的止盈逻辑不变
