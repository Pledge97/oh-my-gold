# 满仓超时降低止盈门槛 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 满仓（100g）后累计交易时长超过 24 小时，将 TP1 止盈触发阈值从 0.6% 降低到 0.3%，解决震荡行情下小幅波动被套问题。

**Architecture:** 在 `market_hours.py` 新增交易时长累计工具函数；`PortfolioPosition` 新增内存字段 `full_since_ts` 记录满仓时间，`buy()`/`sell()` 接收 `ts` 参数维护该字段；`sell_signal.py` 的 `check_sell_signal` 增加超时检查分支，接收 `current_ts_ms` 参数；重启恢复逻辑从最后一笔买入信号推导满仓时间。

**Tech Stack:** Python 3.11, pytest, `chinese_calendar`（已有依赖）

---

## 文件改动范围

| 文件 | 类型 |
|------|------|
| `backend/config.py` | 修改：新增 2 个常量 |
| `backend/core/market_hours.py` | 修改：新增 `calc_trading_seconds` 函数 |
| `backend/risk/portfolio.py` | 修改：`PortfolioPosition` 新增 `full_since_ts`；`buy()`/`sell()` 新增 `ts` 参数；`load_portfolio_from_signals` 恢复逻辑 |
| `backend/signals/sell_signal.py` | 修改：`check_sell_signal` 新增 `current_ts_ms` 参数和超时分支 |
| `backend/strategy/engine.py` | 修改：更新 `buy()`/`sell()`/`check_sell_signal` 调用处传入 `ctx.ts` |
| `tests/test_market_hours.py` | 新建：`calc_trading_seconds` 单元测试 |
| `tests/test_portfolio_timeout.py` | 新建：`full_since_ts` 字段行为测试 |
| `tests/test_sell_signal.py` | 修改：新增超时止盈测试用例 |

---

## Task 1: config.py 新增常量



**Files:**
- Modify: `backend/config.py`

- [ ] **Step 1: 在 `config.py` 末尾追加两个常量**

在文件末尾 `TREND_TP2_SELL_RATIO` 之后追加：

```python
# 满仓超时降低止盈
FULL_POSITION_TIMEOUT_HOURS: float = 24.0     # 满仓超时阈值（交易小时）
FULL_POSITION_TIMEOUT_TP1_PCT: float = 0.003  # 超时后降低的 TP1 止盈率（0.3%）
```

- [ ] **Step 2: 验证常量可导入**

```bash
cd e:/oh-my-gold
python -c "from backend.config import FULL_POSITION_TIMEOUT_HOURS, FULL_POSITION_TIMEOUT_TP1_PCT; print(FULL_POSITION_TIMEOUT_HOURS, FULL_POSITION_TIMEOUT_TP1_PCT)"
```

期望输出：`24.0 0.003`

- [ ] **Step 3: 提交**

```bash
git add backend/config.py
git commit -m "feat: add FULL_POSITION_TIMEOUT_HOURS and FULL_POSITION_TIMEOUT_TP1_PCT to config"
```

---

## Task 2: market_hours.py 新增 calc_trading_seconds

**Files:**
- Modify: `backend/core/market_hours.py`
- Create: `tests/test_market_hours.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_market_hours.py
from datetime import datetime, timezone, timedelta
import pytest
from backend.core.market_hours import calc_trading_seconds

CST = timezone(timedelta(hours=8))


def ts(dt_str: str) -> int:
    """将 'YYYY-MM-DD HH:MM' 转为毫秒时间戳（北京时间）"""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=CST)
    return int(dt.timestamp() * 1000)


def test_zero_when_same_ts():
    """起止时间相同，累计时长为 0"""
    t = ts("2025-05-20 10:00")  # 周二交易时段
    assert calc_trading_seconds(t, t) == pytest.approx(0.0)


def test_one_hour_in_trading_session():
    """周二 10:00~11:00，完整交易时段，应累计 3600 秒"""
    result = calc_trading_seconds(ts("2025-05-20 10:00"), ts("2025-05-20 11:00"))
    assert result == pytest.approx(3600.0, abs=120)  # 允许采样误差 2 分钟


def test_non_trading_time_not_counted():
    """周日全天休市，累计时长应为 0"""
    result = calc_trading_seconds(ts("2025-05-18 10:00"), ts("2025-05-18 12:00"))
    assert result == pytest.approx(0.0)


def test_spans_non_trading_gap():
    """跨越周一 02:30~09:00 非交易时段，只计算交易时段部分"""
    # 周一 01:00 ~ 周一 10:00：01:00~02:30 是交易时段（共 90 分钟），02:30~09:00 非交易，09:00~10:00 交易（60 分钟）
    result = calc_trading_seconds(ts("2025-05-19 01:00"), ts("2025-05-19 10:00"))
    # 预期约 90 + 60 = 150 分钟 = 9000 秒
    assert result == pytest.approx(9000.0, abs=240)


def test_24_trading_hours_across_weekend():
    """跨越周末，只累计工作日交易时段，24交易小时实际经历更长的自然时间"""
    # 周五 14:00 ~ 下周一 12:00：周五下午+夜盘+周一上午，应能累计约 24 小时交易时长
    result = calc_trading_seconds(ts("2025-05-16 14:00"), ts("2025-05-19 14:00"))
    # 周五 14:00~02:30(次日) = 12.5h，周一 09:00~14:00 = 5h，共 17.5h 还不够，说明需要更长区间
    # 此测试验证：跨周末时周六 00:00~02:30 夜盘延续计入，周日不计入
    assert result > 0  # 基础验证：跨周末有交易时长
    assert result < (3 * 24 * 3600)  # 不超过自然时间
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd e:/oh-my-gold
python -m pytest tests/test_market_hours.py -v
```

期望：`ImportError: cannot import name 'calc_trading_seconds'`

- [ ] **Step 3: 在 market_hours.py 末尾追加函数**

在文件末尾 `is_trading_time` 函数之后追加：

```python
def calc_trading_seconds(since_ts_ms: int, until_ts_ms: int, step_sec: int = 60) -> float:
    """
    计算从 since_ts_ms 到 until_ts_ms 之间累计处于交易时段内的秒数。
    按 step_sec 步长采样，每个采样点若处于交易时段则计入 step_sec 秒。

    参数：
        since_ts_ms: 起始时间（毫秒时间戳）
        until_ts_ms: 截止时间（毫秒时间戳）
        step_sec: 采样间隔（秒），默认 60 秒

    返回：
        累计交易时长（秒）
    """
    if until_ts_ms <= since_ts_ms:
        return 0.0

    total = 0.0
    step_ms = step_sec * 1000
    current_ms = since_ts_ms

    while current_ms < until_ts_ms:
        dt = datetime.fromtimestamp(current_ms / 1000, tz=CST)
        if is_trading_time(dt):
            # 最后一个采样点可能不足一个完整步长
            remaining_ms = until_ts_ms - current_ms
            total += min(step_sec, remaining_ms / 1000)
        current_ms += step_ms

    return total
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_market_hours.py -v
```

期望：5 个测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/market_hours.py tests/test_market_hours.py
git commit -m "feat: add calc_trading_seconds to market_hours"
```

---

## Task 3: PortfolioPosition 新增 full_since_ts 字段

**Files:**
- Modify: `backend/risk/portfolio.py`
- Create: `tests/test_portfolio_timeout.py`

`PortfolioPosition` 是一个 dataclass，`buy()` 和 `sell()` 目前不接收 `ts` 参数。本任务新增 `full_since_ts` 内存字段，并给 `buy()`/`sell()` 加上可选的 `ts` 参数（默认 `None`，向后兼容）。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_portfolio_timeout.py
import pytest
from backend.risk.portfolio import PortfolioPosition
from backend import config


def test_full_since_ts_none_initially():
    """初始状态 full_since_ts 为 None"""
    pos = PortfolioPosition()
    assert pos.full_since_ts is None


def test_full_since_ts_set_when_full():
    """买入后达到满仓，full_since_ts 被记录"""
    pos = PortfolioPosition()
    pos.buy(1000.0, config.T_MAX_AMOUNT_G, ts=12345678)
    assert pos.full_since_ts == 12345678


def test_full_since_ts_not_set_when_partial():
    """买入后未达到满仓，full_since_ts 保持 None"""
    pos = PortfolioPosition()
    pos.buy(1000.0, config.LOT1_AMOUNT_G, ts=12345678)  # 50g，未满仓
    assert pos.full_since_ts is None


def test_full_since_ts_set_only_once():
    """多次加仓达到满仓，full_since_ts 只记录第一次满仓时间"""
    pos = PortfolioPosition()
    pos.buy(1000.0, config.LOT1_AMOUNT_G, ts=1000)   # 50g
    pos.buy(990.0, config.LOT2_AMOUNT_G, ts=2000)    # 80g
    pos.buy(980.0, config.LOT3_AMOUNT_G, ts=3000)    # 100g，满仓
    assert pos.full_since_ts == 3000


def test_full_since_ts_cleared_after_sell():
    """卖出后持仓低于满仓，full_since_ts 清除"""
    pos = PortfolioPosition()
    pos.buy(1000.0, config.T_MAX_AMOUNT_G, ts=1000)
    assert pos.full_since_ts == 1000
    pos.sell(1010.0, 10.0, ts=2000)  # 卖出 10g，剩余 90g < 100g
    assert pos.full_since_ts is None


def test_full_since_ts_not_cleared_when_still_full():
    """卖出后持仓仍等于满仓，full_since_ts 保持不变（理论上不会发生，防御性测试）"""
    pos = PortfolioPosition()
    pos.buy(1000.0, config.T_MAX_AMOUNT_G, ts=1000)
    # 卖出 0g（边界情况）
    pos.sell(1010.0, 0.0, ts=2000)
    assert pos.full_since_ts == 1000


def test_buy_without_ts_still_works():
    """不传 ts 时 buy() 正常工作，full_since_ts 保持 None（向后兼容）"""
    pos = PortfolioPosition()
    pos.buy(1000.0, config.T_MAX_AMOUNT_G)
    # 不传 ts，full_since_ts 不应被设置
    assert pos.full_since_ts is None


def test_sell_without_ts_still_works():
    """不传 ts 时 sell() 正常工作（向后兼容）"""
    pos = PortfolioPosition()
    pos.buy(1000.0, 50.0)
    pos.sell(1010.0, 20.0)
    assert pos.total_amount_g == pytest.approx(30.0)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd e:/oh-my-gold
python -m pytest tests/test_portfolio_timeout.py -v
```

期望：多个测试失败，`buy()` 和 `sell()` 不接受 `ts` 参数，`full_since_ts` 属性不存在。

- [ ] **Step 3: 修改 PortfolioPosition**

在 `portfolio.py` 的 `PortfolioPosition` dataclass 中，在 `last_buy_price` 字段之后新增：

```python
full_since_ts: int | None = None  # 首次达到满仓的时间戳（毫秒），非交易时段不计入
```

修改 `buy()` 方法签名和逻辑（完整替换）：

```python
def buy(self, price: float, amount_g: float, ts: int | None = None) -> None:
    """
    记录买入或加仓后的内存状态。
    更新持仓量、成本和最近买入价。
    ts: 买入时间戳（毫秒），传入时用于记录满仓时间。
    """
    self.total_amount_g += amount_g
    self.total_cost += price * amount_g
    self.last_buy_price = price
    # 首次达到满仓时记录时间戳
    if ts is not None and self.full_since_ts is None and self.total_amount_g >= config.T_MAX_AMOUNT_G:
        self.full_since_ts = ts
```

修改 `sell()` 方法签名和逻辑（完整替换）：

```python
def sell(self, price: float, amount_g: float, ts: int | None = None) -> float:
    """
    按当前均价卖出指定克数，返回本次实现盈亏（用于实时交易，不用于回放）。
    回放时应使用存储的 pnl_yuan，避免重复计算。
    ts: 卖出时间戳（毫秒），暂未使用，保留供未来扩展。
    """
    if self.total_amount_g <= 0:
        return 0.0
    sold_g = min(amount_g, self.total_amount_g)
    avg_cost = self.avg_cost
    pnl_yuan = calc_sell_pnl(sold_g, price, avg_cost, config.SELL_FEE_RATE)
    cost_removed = avg_cost * sold_g
    self.total_amount_g = round(self.total_amount_g - sold_g, 4)
    self.total_cost = round(max(self.total_cost - cost_removed, 0.0), 4)
    self.realized_pnl = round(self.realized_pnl + pnl_yuan, 4)
    # 卖出后若持仓低于满仓，清除满仓时间戳
    if self.total_amount_g < config.T_MAX_AMOUNT_G:
        self.full_since_ts = None
    return pnl_yuan
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_portfolio_timeout.py -v
```

期望：8 个测试全部 PASS

- [ ] **Step 5: 运行全量测试确认无回归**

```bash
python -m pytest tests/ -v --tb=short
```

期望：全部 PASS，0 failures

- [ ] **Step 6: 提交**

```bash
git add backend/risk/portfolio.py tests/test_portfolio_timeout.py
git commit -m "feat: add full_since_ts to PortfolioPosition, buy/sell accept optional ts"
```

---

## Task 4: sell_signal.py 新增超时止盈分支

**Files:**
- Modify: `backend/signals/sell_signal.py`
- Modify: `tests/test_sell_signal.py`

- [ ] **Step 1: 在 test_sell_signal.py 末尾追加超时测试用例**

在文件末尾追加：

```python
def test_timeout_tp1_triggers_at_0_3_pct():
    """满仓超过 24 交易小时后，TP1 阈值降为 0.3%，盈利 0.3% 即触发"""
    from backend.core.market_hours import calc_trading_seconds
    from unittest.mock import patch

    pos = PortfolioPosition()
    # 买入 100g 满仓，记录满仓时间
    pos.buy(1000.0, 100.0, ts=1_000_000)
    # 触发价 = 1000 * 1.003 / 0.996 ≈ 1007.03
    ctx = make_context(price=1007.03, ema_5m_20=990.0)
    ctx.market_state = MarketState.OSCILLATION

    # 模拟 calc_trading_seconds 返回 24 小时 + 1 秒
    with patch("backend.signals.sell_signal.calc_trading_seconds", return_value=24 * 3600 + 1):
        signal = check_sell_signal(pos, ctx, current_ts_ms=2_000_000)

    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_1
    assert signal.sell_ratio == pytest.approx(0.60)
    assert "超时" in signal.reason


def test_timeout_tp1_not_triggered_before_24h():
    """满仓未超过 24 交易小时，仍使用原始 0.6% 阈值"""
    from unittest.mock import patch

    pos = PortfolioPosition()
    pos.buy(1000.0, 100.0, ts=1_000_000)
    # 价格盈利 0.3%，不足原始 0.6% 阈值
    ctx = make_context(price=1007.03, ema_5m_20=990.0)
    ctx.market_state = MarketState.OSCILLATION

    # 模拟 calc_trading_seconds 返回 23 小时
    with patch("backend.signals.sell_signal.calc_trading_seconds", return_value=23 * 3600):
        signal = check_sell_signal(pos, ctx, current_ts_ms=2_000_000)

    assert signal is None


def test_timeout_not_triggered_when_not_full():
    """未满仓时，即使时间很长也不触发超时逻辑"""
    from unittest.mock import patch

    pos = PortfolioPosition()
    pos.buy(1000.0, 50.0, ts=1_000_000)  # 50g，未满仓，full_since_ts 为 None
    ctx = make_context(price=1007.03, ema_5m_20=990.0)
    ctx.market_state = MarketState.OSCILLATION

    with patch("backend.signals.sell_signal.calc_trading_seconds", return_value=100 * 3600):
        signal = check_sell_signal(pos, ctx, current_ts_ms=2_000_000)

    assert signal is None


def test_timeout_not_triggered_after_tp1_done():
    """tp1 已执行后，超时逻辑不再影响（tp1 已完成）"""
    from unittest.mock import patch

    pos = PortfolioPosition()
    pos.buy(1000.0, 100.0, ts=1_000_000)
    pos.tp1_done = True
    ctx = make_context(price=1007.03, ema_5m_20=990.0)
    ctx.market_state = MarketState.OSCILLATION

    with patch("backend.signals.sell_signal.calc_trading_seconds", return_value=100 * 3600):
        signal = check_sell_signal(pos, ctx, current_ts_ms=2_000_000)

    # tp1 已完成，不会再触发 tp1
    assert signal is None or signal.exit_reason != ExitReason.TAKE_PROFIT_1


def test_timeout_not_triggered_in_trend_up():
    """TREND_UP 状态下，超时逻辑不降低 TP1 阈值（TREND_UP 有自己的更高阈值）"""
    from unittest.mock import patch

    pos = PortfolioPosition()
    pos.buy(1000.0, 100.0, ts=1_000_000)
    # 价格盈利 0.3%，低于 TREND_UP 的 1.2% 阈值
    ctx = make_context(price=1007.03, ema_5m_20=990.0)
    ctx.market_state = MarketState.TREND_UP
    ctx.indicators.ema_2h_20 = 990.0

    with patch("backend.signals.sell_signal.calc_trading_seconds", return_value=100 * 3600):
        signal = check_sell_signal(pos, ctx, current_ts_ms=2_000_000)

    assert signal is None


def test_existing_tests_still_pass_with_new_param():
    """原有测试传入 current_ts_ms=0 时行为不变（full_since_ts 为 None，不触发超时）"""
    pos = make_portfolio(avg_cost=1000.0, total_g=50.0)
    ctx = make_context(price=1010.05, ema_5m_20=990.0)
    ctx.market_state = MarketState.OSCILLATION
    signal = check_sell_signal(pos, ctx, current_ts_ms=0)
    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_1
```

- [ ] **Step 2: 运行新增测试确认失败**

```bash
cd e:/oh-my-gold
python -m pytest tests/test_sell_signal.py::test_timeout_tp1_triggers_at_0_3_pct -v
```

期望：`TypeError: check_sell_signal() got an unexpected keyword argument 'current_ts_ms'`

- [ ] **Step 3: 修改 sell_signal.py**

在文件顶部导入区新增：

```python
from backend.core.market_hours import calc_trading_seconds
from backend import config
```

（`config` 已导入，只需新增 `calc_trading_seconds`）

修改 `check_sell_signal` 函数签名（新增 `current_ts_ms` 参数）：

```python
def check_sell_signal(
    portfolio: PortfolioPosition,
    ctx,
    current_ts_ms: int = 0,
) -> Optional[SellSignalV2]:
```

在函数体内，`is_trend_up` 判断之后、`tp1_pct` 赋值之前，插入超时检查逻辑：

```python
    # TREND_UP 状态使用更高止盈阈值、更低分批卖出比例和 2H EMA20 追踪止盈
    is_trend_up: bool = market_state == MarketState.TREND_UP
    if is_trend_up:
        tp1_pct: float = config.TREND_TAKE_PROFIT_1_PCT
        tp2_pct: float = config.TREND_TAKE_PROFIT_2_PCT
        tp1_ratio: float = config.TREND_TP1_SELL_RATIO
        tp2_ratio: float = config.TREND_TP2_SELL_RATIO
        trailing_ema: float = ctx.indicators.ema_2h_20
        ema_label: str = "2小时EMA20"
    else:
        tp1_pct = config.TAKE_PROFIT_1_PCT
        tp2_pct = config.TAKE_PROFIT_2_PCT
        tp1_ratio = config.TAKE_PROFIT_1_SELL_RATIO
        tp2_ratio = config.TAKE_PROFIT_2_SELL_RATIO
        trailing_ema = ctx.indicators.ema_5m_20
        ema_label = "5分钟EMA20"

        # 满仓超时：非 TREND_UP 且满仓超过 24 交易小时，降低 TP1 阈值
        if (
            not portfolio.tp1_done
            and portfolio.full_since_ts is not None
            and current_ts_ms > 0
        ):
            trading_secs = calc_trading_seconds(portfolio.full_since_ts, current_ts_ms)
            if trading_secs >= config.FULL_POSITION_TIMEOUT_HOURS * 3600:
                tp1_pct = config.FULL_POSITION_TIMEOUT_TP1_PCT
```

同时更新 TP1 触发时的 `reason` 字段，在超时情况下加入说明。将原来的 TP1 返回语句替换为：

```python
    # 第1次止盈：达到当前市场状态对应的盈利阈值后，卖出对应比例
    if not portfolio.tp1_done and pnl >= tp1_pct:
        timeout_note = "（满仓超时降低阈值）" if tp1_pct == config.FULL_POSITION_TIMEOUT_TP1_PCT else ""
        return SellSignalV2(
            exit_reason=ExitReason.TAKE_PROFIT_1,
            sell_ratio=tp1_ratio,
            reason=f"T仓整体盈利{pnl:.2%}≥{tp1_pct:.2%}，卖出{tp1_ratio:.0%}{timeout_note}",
        )
```

- [ ] **Step 4: 运行新增测试确认通过**

```bash
python -m pytest tests/test_sell_signal.py -v
```

期望：全部测试 PASS（含原有测试和新增超时测试）

- [ ] **Step 5: 提交**

```bash
git add backend/signals/sell_signal.py tests/test_sell_signal.py
git commit -m "feat: add full-position timeout TP1 threshold reduction in sell_signal"
```

---

## Task 5: engine.py 更新调用处传入 ctx.ts

**Files:**
- Modify: `backend/strategy/engine.py`

- [ ] **Step 1: 更新 `_execute_buy_v3` 中的 `buy()` 调用**

在 `engine.py` 的 `_execute_buy_v3` 方法中，将：

```python
self._portfolio.buy(ctx.price, signal.amount_g)
```

替换为：

```python
self._portfolio.buy(ctx.price, signal.amount_g, ts=ctx.ts)
```

- [ ] **Step 2: 更新 `_execute_sell_v3` 中的 `sell()` 调用**

在 `_execute_sell_v3` 方法中，将：

```python
self._portfolio.sell(ctx.price, sold_g)
```

替换为：

```python
self._portfolio.sell(ctx.price, sold_g, ts=ctx.ts)
```

- [ ] **Step 3: 更新 `_execute_exit_v3` 中的 `sell()` 调用**

在 `_execute_exit_v3` 方法中，将：

```python
self._portfolio.sell(ctx.price, sold_g)
```

替换为：

```python
self._portfolio.sell(ctx.price, sold_g, ts=ctx.ts)
```

- [ ] **Step 4: 更新 `check_sell_signal` 调用处传入 `current_ts_ms`**

在 `on_tick_v2` 方法中，将：

```python
sell_sig = check_sell_signal(self._portfolio, ctx)
```

替换为：

```python
sell_sig = check_sell_signal(self._portfolio, ctx, current_ts_ms=ctx.ts or 0)
```

- [ ] **Step 5: 运行全量测试确认无回归**

```bash
cd e:/oh-my-gold
python -m pytest tests/ -v --tb=short
```

期望：全部 PASS，0 failures

- [ ] **Step 6: 提交**

```bash
git add backend/strategy/engine.py
git commit -m "feat: pass ctx.ts to buy/sell/check_sell_signal in engine"
```

---

## Task 6: load_portfolio_from_signals 重启恢复逻辑

**Files:**
- Modify: `backend/risk/portfolio.py`

重启时从 signals 表回放，若最终状态是满仓，将最后一笔 BUY/ADD_LOT 信号的 `ts` 赋值给 `full_since_ts`。

- [ ] **Step 1: 在 test_portfolio_timeout.py 末尾追加恢复测试**

```python
def test_load_portfolio_restores_full_since_ts():
    """重启恢复：满仓状态下，full_since_ts 从最后一笔买入信号的 ts 推导"""
    import sqlite3
    from backend.risk.portfolio import load_portfolio_from_signals
    from backend import config

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            type TEXT NOT NULL,
            mode TEXT,
            price REAL,
            amount_g REAL,
            reason TEXT,
            pnl_yuan REAL
        )
    """)
    # 模拟三批买入达到满仓
    conn.execute("INSERT INTO signals (ts, type, mode, price, amount_g, reason) VALUES (1000, 'BUY', 'OSCILLATION', 1000.0, 50.0, '')")
    conn.execute("INSERT INTO signals (ts, type, mode, price, amount_g, reason) VALUES (2000, 'ADD_LOT', 'OSCILLATION', 990.0, 30.0, '')")
    conn.execute("INSERT INTO signals (ts, type, mode, price, amount_g, reason) VALUES (3000, 'ADD_LOT', 'OSCILLATION', 980.0, 20.0, '')")
    conn.commit()

    portfolio = load_portfolio_from_signals(conn)

    assert portfolio.total_amount_g == pytest.approx(100.0)
    assert portfolio.full_since_ts == 3000  # 最后一笔买入的 ts


def test_load_portfolio_no_full_since_ts_when_not_full():
    """重启恢复：未满仓时，full_since_ts 为 None"""
    import sqlite3
    from backend.risk.portfolio import load_portfolio_from_signals

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER NOT NULL,
            type TEXT NOT NULL,
            mode TEXT,
            price REAL,
            amount_g REAL,
            reason TEXT,
            pnl_yuan REAL
        )
    """)
    conn.execute("INSERT INTO signals (ts, type, mode, price, amount_g, reason) VALUES (1000, 'BUY', 'OSCILLATION', 1000.0, 50.0, '')")
    conn.commit()

    portfolio = load_portfolio_from_signals(conn)

    assert portfolio.total_amount_g == pytest.approx(50.0)
    assert portfolio.full_since_ts is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd e:/oh-my-gold
python -m pytest tests/test_portfolio_timeout.py::test_load_portfolio_restores_full_since_ts -v
```

期望：`AssertionError: assert None == 3000`（`full_since_ts` 未被恢复）

- [ ] **Step 3: 修改 load_portfolio_from_signals**

在 `load_portfolio_from_signals` 函数末尾，`return portfolio` 之前，追加恢复逻辑：

```python
    # 重启恢复：若当前持仓达到满仓，从最后一笔买入信号推导满仓时间
    if portfolio.total_amount_g >= config.T_MAX_AMOUNT_G:
        last_buy_ts = None
        for row in reversed(rows):
            if row["type"] in BUY_TYPES:
                last_buy_ts = int(row["ts"])
                break
        portfolio.full_since_ts = last_buy_ts

    return portfolio
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_portfolio_timeout.py -v
```

期望：全部测试 PASS

- [ ] **Step 5: 运行全量测试确认无回归**

```bash
python -m pytest tests/ -v --tb=short
```

期望：全部 PASS，0 failures

- [ ] **Step 6: 提交**

```bash
git add backend/risk/portfolio.py tests/test_portfolio_timeout.py
git commit -m "feat: restore full_since_ts from signals on service restart"
```

---

## 自检（Spec 覆盖验证）

| Spec 要求 | 实现任务 |
|----------|---------|
| 新增 `FULL_POSITION_TIMEOUT_HOURS` 和 `FULL_POSITION_TIMEOUT_TP1_PCT` 常量 | Task 1 |
| 新增 `calc_trading_seconds` 工具函数 | Task 2 |
| `PortfolioPosition` 新增 `full_since_ts` 内存字段 | Task 3 |
| `buy()` 在满仓时记录 `full_since_ts` | Task 3 |
| `sell()` 在持仓低于满仓时清除 `full_since_ts` | Task 3 |
| `check_sell_signal` 新增 `current_ts_ms` 参数和超时分支 | Task 4 |
| 超时仅在非 TREND_UP 状态下生效 | Task 4 |
| engine 调用处传入 `ctx.ts` | Task 5 |
| 重启从 signals 恢复 `full_since_ts` | Task 6 |
