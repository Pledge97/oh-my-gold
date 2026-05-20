# TREND_UP 专属止盈策略设计

## 背景

当前止盈逻辑（`sell_signal.py`）不区分市场状态，所有模式使用相同的阈值和卖出比例。在趋势上涨（TREND_UP）行情中，这会导致过早止盈，错失趋势行情的大幅上涨。

## 目标

在 TREND_UP 状态下：
- 抬高止盈触发阈值，让利润跑得更远
- 减少每次止盈卖出比例，保留更多仓位吃趋势
- 追踪止盈改用 2H EMA20，过滤 5 分钟级别噪声

## 设计

### 1. 新增 2H K线和 EMA 指标

**scheduler.py：**
- 新增 `_kline_2h_cache`，在 `_refresh_slow_indicators` 中与 4H K线同频重建（每小时一次，`period_sec=7200`）
- 需要至少 `EMA_SHORT=20` 根 2H K线（约 40 小时 ≈ 2 天）才计算 EMA
- 计算结果存入 `IndicatorSnapshot.ema_2h_20`

**context.py：**
- `IndicatorSnapshot` 新增字段 `ema_2h_20: float = 0.0`

### 2. 新增 TREND_UP 止盈配置

**config.py 新增：**

```python
TREND_TAKE_PROFIT_1_PCT: float = 0.012     # TREND_UP 止盈1触发盈利率
TREND_TAKE_PROFIT_2_PCT: float = 0.020     # TREND_UP 止盈2触发盈利率
TREND_TP1_SELL_RATIO: float = 0.40         # TREND_UP 止盈1卖出比例（占当前持仓）
TREND_TP2_SELL_RATIO: float = 0.30         # TREND_UP 止盈2卖出比例（占初始仓位）
```

### 3. sell_signal.py 分支逻辑

`check_sell_signal` 增加 `market_state` 参数，TREND_UP 时走专属分支：

| 阶段 | 非 TREND_UP | TREND_UP |
|------|------------|----------|
| TP1 触发条件 | 盈利 >= 0.6% | 盈利 >= 1.2% |
| TP1 卖出比例 | 当前持仓 60% | 当前持仓 40% |
| TP2 触发条件 | 盈利 >= 1.2% | 盈利 >= 2.0% |
| TP2 卖出比例 | 初始仓位 20%（剩余 50%）| 初始仓位 30%（剩余 50%）|
| 追踪止盈触发 | 价格跌破 5分钟 EMA20 | 价格跌破 2H EMA20 |
| 追踪止盈卖出 | 全清剩余仓位 | 全清剩余仓位（初始 30%）|

TREND_UP 三次止盈合计：40% + 30% + 30% = 100%，全部清仓。

### 4. engine.py 调用更新

`check_sell_signal` 调用处传入 `ctx.market_state`。

## 影响范围

- `backend/config.py`：新增 4 个常量
- `backend/core/context.py`：`IndicatorSnapshot` 新增 `ema_2h_20`
- `backend/core/scheduler.py`：新增 2H K线构建和 EMA 计算
- `backend/signals/sell_signal.py`：增加 `market_state` 参数和 TREND_UP 分支
- `backend/strategy/engine.py`：更新 `check_sell_signal` 调用

## 不变的部分

- 止损逻辑（`exit_signal.py`）不变
- 买入逻辑（`buy_signal.py`）不变
- 非 TREND_UP 状态的止盈逻辑不变

## 实现完成

- 已新增 TREND_UP 止盈配置常量（`backend/config.py`）
- 已新增 `IndicatorSnapshot.ema_2h_20` 字段（`backend/core/context.py`）
- 已新增 2H K线构建和 EMA20 计算缓存（`backend/core/scheduler.py`）
- 已在 `sell_signal.py` 增加 TREND_UP 分支逻辑
- 已验证 `engine.py` 继续传入完整 `ctx`，无需额外改动

**测试覆盖：**

- 单元测试：`tests/test_context.py`
- 回归测试：`tests/test_scheduler_2h.py`
- 卖出信号测试：`tests/test_sell_signal.py`
- 端到端流程测试：`tests/test_trend_up_integration.py`
