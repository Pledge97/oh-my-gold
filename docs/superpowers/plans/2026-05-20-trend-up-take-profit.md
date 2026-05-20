# TREND_UP 专属止盈策略实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 TREND_UP 状态下使用更高的止盈阈值和更慢的追踪止盈（2H EMA20），让利润跑得更远

**Architecture:** 新增 2H K线构建和 EMA 计算，在 sell_signal.py 中根据 market_state 分支选择不同的止盈参数和追踪指标

**Tech Stack:** Python 3.11, pandas, ta (技术指标库), pytest

---

## Task 1: 新增 TREND_UP 止盈配置常量

**Files:**
- Modify: `backend/config.py:79-84`

- [ ] **Step 1: 在 config.py 组合止盈阈值部分新增 TREND_UP 专属常量**

在 `TAKE_PROFIT_2_SELL_RATIO` 后面新增：

```python
# 组合止盈阈值
TAKE_PROFIT_1_PCT: float = 0.006   # 第1次止盈触发盈利率
TAKE_PROFIT_2_PCT: float = 0.012   # 第2次止盈触发盈利率
TAKE_PROFIT_1_SELL_RATIO: float = 0.60  # 第1次止盈卖出比例
TAKE_PROFIT_2_SELL_RATIO: float = 0.20  # 第2次止盈卖出比例

# TREND_UP 专属止盈阈值
TREND_TAKE_PROFIT_1_PCT: float = 0.012     # TREND_UP 止盈1触发盈利率（1.2%）
TREND_TAKE_PROFIT_2_PCT: float = 0.020     # TREND_UP 止盈2触发盈利率（2.0%）
TREND_TP1_SELL_RATIO: float = 0.40         # TREND_UP 止盈1卖出比例
TREND_TP2_SELL_RATIO: float = 0.30         # TREND_UP 止盈2卖出比例（占初始仓位）
```

- [ ] **Step 2: 提交配置变更**

```bash
git add backend/config.py
git commit -m "feat: add TREND_UP take-profit config constants"
```

---

## Task 2: 新增 IndicatorSnapshot.ema_2h_20 字段

**Files:**
- Modify: `backend/core/context.py:9-24`

- [ ] **Step 1: 写失败测试 - 验证 ema_2h_20 字段存在且默认为 0.0**

Create: `tests/test_context.py`

```python
# tests/test_context.py
from backend.core.context import IndicatorSnapshot


def test_indicator_snapshot_has_ema_2h_20():
    """IndicatorSnapshot 应包含 ema_2h_20 字段，默认值为 0.0"""
    snapshot = IndicatorSnapshot()
    assert hasattr(snapshot, "ema_2h_20")
    assert snapshot.ema_2h_20 == 0.0
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/test_context.py::test_indicator_snapshot_has_ema_2h_20 -v
```

预期输出：`AttributeError: 'IndicatorSnapshot' object has no attribute 'ema_2h_20'`

- [ ] **Step 3: 在 IndicatorSnapshot 新增 ema_2h_20 字段**

在 `ema_4h_60` 后面新增：

```python
@dataclass
class IndicatorSnapshot:
    adx: float = 0.0
    plus_di: float = 0.0
    minus_di: float = 0.0
    adx_series: Optional[pd.Series] = None
    bb_upper: float = 0.0
    bb_mid: float = 0.0
    bb_lower: float = 0.0
    rsi: float = 50.0
    atr_5m: float = 0.0
    atr_daily_mean: float = 0.0
    ema_5m_20: float = 0.0
    ema_4h_20: float = 0.0
    ema_4h_60: float = 0.0
    ema_2h_20: float = 0.0  # 2小时 EMA20，用于 TREND_UP 追踪止盈
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/test_context.py::test_indicator_snapshot_has_ema_2h_20 -v
```

预期输出：`PASSED`

- [ ] **Step 5: 提交**

```bash
git add backend/core/context.py tests/test_context.py
git commit -m "feat: add ema_2h_20 field to IndicatorSnapshot"
```

---

## Task 3: scheduler.py 新增 2H K线构建和 EMA 计算

**Files:**
- Modify: `backend/core/scheduler.py:34-40` (新增缓存变量)
- Modify: `backend/core/scheduler.py:90-109` (在 _refresh_slow_indicators 中新增 2H K线构建)
- Modify: `backend/core/scheduler.py:160-174` (在 _update_context 中填充 ema_2h_20)

- [ ] **Step 1: 写失败测试 - 验证 2H K线构建逻辑**

Create: `tests/test_scheduler_2h.py`

```python
# tests/test_scheduler_2h.py
import pandas as pd
from backend.data.kline import build_kline


def test_2h_kline_builds_correctly():
    """验证 2H K线构建逻辑（period_sec=7200）"""
    # 模拟 4 小时的 tick 数据（每秒一个，共 14400 个）
    ticks = [{"ts": i * 1000, "price": 1000.0 + (i % 100) * 0.1} for i in range(14400)]
    kline_2h = build_kline(ticks, period_sec=7200)
    
    # 应该产生 2 根 2H K线
    assert len(kline_2h) == 2
    assert "open" in kline_2h.columns
    assert "high" in kline_2h.columns
    assert "low" in kline_2h.columns
    assert "close" in kline_2h.columns
```

- [ ] **Step 2: 运行测试验证通过（build_kline 已存在，这是回归测试）**

```bash
python -m pytest tests/test_scheduler_2h.py::test_2h_kline_builds_correctly -v
```

预期输出：`PASSED`

- [ ] **Step 3: 在 scheduler.py 新增 2H K线缓存变量**

在 `_kline_4h_cache` 后面新增：

```python
# 慢速指标缓存
_kline_4h_cache: pd.DataFrame = pd.DataFrame()
_kline_2h_cache: pd.DataFrame = pd.DataFrame()  # 2小时K线缓存
_daily_df_cache: pd.DataFrame = pd.DataFrame()
_ema_4h_20_cache: float = 0.0
_ema_4h_60_cache: float = 0.0
_ema_2h_20_cache: float = 0.0  # 2小时 EMA20 缓存
_adx_cache: dict = {"adx": 0.0, "plus_di": 0.0, "minus_di": 0.0, "adx_series": None}
_atr_daily_mean_cache: float = 0.0
```

- [ ] **Step 4: 在 _refresh_slow_indicators 函数签名的 global 声明中新增 2H 变量**

修改 `_refresh_slow_indicators` 函数开头的 global 声明：

```python
def _refresh_slow_indicators(now: float) -> None:
    """按频率刷新4H K线和日线指标，避免每5秒全量重算"""
    global _kline_4h_cache, _kline_2h_cache, _ema_4h_20_cache, _ema_4h_60_cache, _ema_2h_20_cache
    global _daily_df_cache, _adx_cache, _atr_daily_mean_cache
    global _last_4h_refresh, _last_daily_refresh_date
```

- [ ] **Step 5: 在 _refresh_slow_indicators 的 4H K线构建后新增 2H K线构建**

在 `_last_4h_refresh = now` 后面、日线 ADX 计算前新增：

```python
        _last_4h_refresh = now
        print(f"[kline] 4小时K线计算完成，{len(_kline_4h_cache)} 根，耗时 {time.time()-t0:.3f}s")

        # 2H K线：与 4H 同频重建（每小时一次）
        print(f"[kline] 开始计算2小时K线（{len(ticks)} 条 tick）")
        t0 = time.time()
        _kline_2h_cache = build_kline(ticks, period_sec=7200)
        if not _kline_2h_cache.empty and len(_kline_2h_cache) >= config.EMA_SHORT:
            _ema_2h_20_cache = float(calc_ema(_kline_2h_cache, config.EMA_SHORT).iloc[-1])
        else:
            _ema_2h_20_cache = 0.0
        print(f"[kline] 2小时K线计算完成，{len(_kline_2h_cache)} 根，耗时 {time.time()-t0:.3f}s")

    # 日线ADX：每天 00:01 后首次 tick 时刷新
```

- [ ] **Step 6: 在 _update_context 中填充 ema_2h_20 到 IndicatorSnapshot**

修改 `ctx.indicators = IndicatorSnapshot(...)` 调用，新增 `ema_2h_20` 参数：

```python
        ctx.indicators = IndicatorSnapshot(
            adx=_adx_cache["adx"],
            plus_di=_adx_cache["plus_di"],
            minus_di=_adx_cache["minus_di"],
            adx_series=_adx_cache["adx_series"],
            bb_upper=bb["upper"],
            bb_mid=bb["mid"],
            bb_lower=bb["lower"],
            rsi=rsi,
            atr_5m=atr_5m,
            atr_daily_mean=_atr_daily_mean_cache,
            ema_5m_20=ema_5m_20,
            ema_4h_20=_ema_4h_20_cache,
            ema_4h_60=_ema_4h_60_cache,
            ema_2h_20=_ema_2h_20_cache,
        )
```

- [ ] **Step 7: 提交**

```bash
git add backend/core/scheduler.py tests/test_scheduler_2h.py
git commit -m "feat: add 2H kline and EMA20 calculation in scheduler"
```

---

## Task 4: sell_signal.py 增加 market_state 参数和 TREND_UP 分支

**Files:**
- Modify: `backend/signals/sell_signal.py:16-66`
- Modify: `backend/strategy/engine.py:47`

- [ ] **Step 1: 写失败测试 - TREND_UP 状态下 TP1 阈值为 1.2%**

Modify: `tests/test_sell_signal.py` (在文件末尾新增)

```python
from backend.core.enums import MarketState


def test_trend_up_tp1_triggers_at_1_2_pct():
    """TREND_UP 状态下，扣除手续费后净盈利达到1.2%时触发第1次止盈"""
    pos = make_portfolio(avg_cost=1000.0, total_g=50.0)
    # 触发价 = 1000 * 1.012 / 0.996 ≈ 1016.07
    ctx = make_context(price=1016.07, ema_5m_20=990.0)
    ctx.market_state = MarketState.TREND_UP
    ctx.indicators.ema_2h_20 = 990.0
    signal = check_sell_signal(pos, ctx)
    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_1
    assert signal.sell_ratio == pytest.approx(0.40)
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/test_sell_signal.py::test_trend_up_tp1_triggers_at_1_2_pct -v
```

预期输出：`TypeError: check_sell_signal() missing 1 required positional argument: 'market_state'` 或 `AssertionError`

- [ ] **Step 3: 修改 check_sell_signal 函数签名，新增 market_state 参数**

```python
def check_sell_signal(
    portfolio: PortfolioPosition,
    ctx,
) -> Optional[SellSignalV2]:
    """
    检查是否触发组合止盈信号（V2）。

    优先级：tp1 > tp2 > 追踪止盈（EMA跌破）

    Args:
        portfolio: 当前 T仓组合持仓
        ctx: MarketContext（或 duck-type 兼容对象），需提供
             ctx.price、ctx.market_state、ctx.indicators.ema_5m_20、ctx.indicators.ema_2h_20

    Returns:
        SellSignalV2 实例，或 None（无信号）
    """
    if portfolio.is_empty():
        return None

    price: float = ctx.price
    market_state = getattr(ctx, "market_state", None)
    pnl: float = portfolio.pnl_pct(price)

    # TREND_UP 状态使用专属止盈参数
    from backend.core.enums import MarketState
    is_trend_up = market_state == MarketState.TREND_UP if market_state else False

    if is_trend_up:
        tp1_pct = config.TREND_TAKE_PROFIT_1_PCT
        tp2_pct = config.TREND_TAKE_PROFIT_2_PCT
        tp1_ratio = config.TREND_TP1_SELL_RATIO
        tp2_ratio = config.TREND_TP2_SELL_RATIO
        trailing_ema = ctx.indicators.ema_2h_20
    else:
        tp1_pct = config.TAKE_PROFIT_1_PCT
        tp2_pct = config.TAKE_PROFIT_2_PCT
        tp1_ratio = config.TAKE_PROFIT_1_SELL_RATIO
        tp2_ratio = config.TAKE_PROFIT_2_SELL_RATIO
        trailing_ema = ctx.indicators.ema_5m_20

    # 第1次止盈
    if not portfolio.tp1_done and pnl >= tp1_pct:
        return SellSignalV2(
            exit_reason=ExitReason.TAKE_PROFIT_1,
            sell_ratio=tp1_ratio,
            reason=f"T仓整体盈利{pnl:.2%}≥{tp1_pct:.2%}，卖出{tp1_ratio:.0%}",
        )

    # 第2次止盈：tp1已执行且盈利≥阈值，卖出初始仓位的指定比例
    # TP1已卖 tp1_ratio，剩余 (1-tp1_ratio)，要卖初始的 tp2_ratio 需要卖剩余的 tp2_ratio/(1-tp1_ratio)
    if portfolio.tp1_done and not portfolio.tp2_done and pnl >= tp2_pct:
        actual_sell_ratio = tp2_ratio / (1 - tp1_ratio)
        return SellSignalV2(
            exit_reason=ExitReason.TAKE_PROFIT_2,
            sell_ratio=actual_sell_ratio,
            reason=f"T仓整体盈利{pnl:.2%}≥{tp2_pct:.2%}，卖出初始仓位的{tp2_ratio:.0%}",
        )

    # 第3次止盈（追踪）：tp1和tp2均已执行，金价跌破 EMA，清空剩余
    if portfolio.tp1_done and portfolio.tp2_done and price < trailing_ema:
        ema_label = "2小时EMA20" if is_trend_up else "5分钟EMA20"
        return SellSignalV2(
            exit_reason=ExitReason.TAKE_PROFIT_TRAILING,
            sell_ratio=1.0,
            reason=f"金价{price:.2f}跌破{ema_label}={trailing_ema:.2f}，清空剩余持仓",
        )

    return None
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/test_sell_signal.py::test_trend_up_tp1_triggers_at_1_2_pct -v
```

预期输出：`PASSED`

- [ ] **Step 5: 新增更多 TREND_UP 测试用例**

在 `tests/test_sell_signal.py` 末尾新增：

```python
def test_trend_up_tp2_triggers_at_2_0_pct():
    """TREND_UP 状态下，盈利达到2.0%时触发第2次止盈，卖出初始仓位的30%"""
    pos = make_portfolio(avg_cost=1000.0, total_g=50.0)
    pos.tp1_done = True
    # 触发价 = 1000 * 1.020 / 0.996 ≈ 1024.10
    ctx = make_context(price=1024.10, ema_5m_20=990.0)
    ctx.market_state = MarketState.TREND_UP
    ctx.indicators.ema_2h_20 = 990.0
    signal = check_sell_signal(pos, ctx)
    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_2
    # TP1已卖40%，剩余60%，要卖初始的30%需要卖剩余的50% (0.3/0.6=0.5)
    assert signal.sell_ratio == pytest.approx(0.50)


def test_trend_up_trailing_uses_2h_ema():
    """TREND_UP 状态下，追踪止盈使用 2H EMA20 而不是 5分钟 EMA20"""
    pos = make_portfolio(avg_cost=1000.0, total_g=20.0)
    pos.tp1_done = True
    pos.tp2_done = True
    # 价格跌破 2H EMA20 但高于 5分钟 EMA20
    ctx = make_context(price=1005.0, ema_5m_20=1001.0)
    ctx.market_state = MarketState.TREND_UP
    ctx.indicators.ema_2h_20 = 1008.0
    signal = check_sell_signal(pos, ctx)
    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_TRAILING
    assert "2小时EMA20" in signal.reason


def test_non_trend_up_uses_original_logic():
    """非 TREND_UP 状态下，使用原始止盈逻辑（0.6%、60%）"""
    pos = make_portfolio(avg_cost=1000.0, total_g=50.0)
    # 触发价 = 1000 * 1.006 / 0.996 ≈ 1010.05
    ctx = make_context(price=1010.05, ema_5m_20=990.0)
    ctx.market_state = MarketState.OSCILLATION
    ctx.indicators.ema_2h_20 = 990.0
    signal = check_sell_signal(pos, ctx)
    assert signal is not None
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_1
    assert signal.sell_ratio == pytest.approx(0.60)
```

- [ ] **Step 6: 运行所有 sell_signal 测试验证通过**

```bash
python -m pytest tests/test_sell_signal.py -v
```

预期输出：所有测试 `PASSED`

- [ ] **Step 7: 提交**

```bash
git add backend/signals/sell_signal.py tests/test_sell_signal.py
git commit -m "feat: add TREND_UP specific take-profit logic in sell_signal"
```

---

## Task 5: engine.py 更新 check_sell_signal 调用（传入 ctx）

**Files:**
- Modify: `backend/strategy/engine.py:47`

- [ ] **Step 1: 确认当前调用方式**

当前 `engine.py:47` 调用：
```python
sell_sig = check_sell_signal(self._portfolio, ctx)
```

已经传入了 `ctx`，无需修改。验证 `ctx` 包含 `market_state` 字段。

- [ ] **Step 2: 运行集成测试验证 engine 调用正确**

```bash
python -m pytest tests/ -k "engine" -v
```

预期输出：所有 engine 相关测试 `PASSED`

- [ ] **Step 3: 如果测试通过，提交一个空 commit 标记此任务完成**

```bash
git commit --allow-empty -m "chore: verify engine.py already passes ctx to check_sell_signal"
```

---

## Task 6: 端到端验证和文档更新

**Files:**
- Create: `tests/test_trend_up_integration.py`
- Modify: `docs/superpowers/specs/2026-05-20-trend-up-take-profit-design.md`

- [ ] **Step 1: 写端到端集成测试**

Create: `tests/test_trend_up_integration.py`

```python
# tests/test_trend_up_integration.py
"""端到端测试：验证 TREND_UP 状态下完整的止盈流程"""
import pytest
from backend.core.context import MarketContext, IndicatorSnapshot
from backend.core.enums import MarketState, ExitReason
from backend.signals.sell_signal import check_sell_signal
from backend.risk.portfolio import PortfolioPosition


def test_trend_up_full_take_profit_flow():
    """TREND_UP 状态下完整止盈流程：TP1(40%) -> TP2(30%) -> 追踪(30%)"""
    # 初始持仓 100g，均价 1000
    portfolio = PortfolioPosition()
    portfolio.buy(1000.0, 100.0)
    
    ctx = MarketContext()
    ctx.market_state = MarketState.TREND_UP
    ctx.indicators = IndicatorSnapshot()
    ctx.indicators.ema_2h_20 = 1000.0
    ctx.indicators.ema_5m_20 = 1000.0
    
    # 阶段1：价格涨到 1016，触发 TP1（1.2%），卖出 40g
    ctx.price = 1016.07
    signal = check_sell_signal(portfolio, ctx)
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_1
    assert signal.sell_ratio == pytest.approx(0.40)
    portfolio.sell(ctx.price, 100.0 * 0.40)  # 卖出 40g，剩余 60g
    portfolio.tp1_done = True
    
    # 阶段2：价格涨到 1024，触发 TP2（2.0%），卖出初始 30g（剩余的 50%）
    ctx.price = 1024.10
    signal = check_sell_signal(portfolio, ctx)
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_2
    assert signal.sell_ratio == pytest.approx(0.50)
    portfolio.sell(ctx.price, 60.0 * 0.50)  # 卖出 30g，剩余 30g
    portfolio.tp2_done = True
    
    # 阶段3：价格回落跌破 2H EMA20，触发追踪止盈，清空剩余 30g
    ctx.price = 1015.0
    ctx.indicators.ema_2h_20 = 1018.0
    signal = check_sell_signal(portfolio, ctx)
    assert signal.exit_reason == ExitReason.TAKE_PROFIT_TRAILING
    assert signal.sell_ratio == pytest.approx(1.0)
    assert "2小时EMA20" in signal.reason
    portfolio.sell(ctx.price, 30.0)  # 清空
    
    assert portfolio.is_empty()
```

- [ ] **Step 2: 运行集成测试**

```bash
python -m pytest tests/test_trend_up_integration.py -v
```

预期输出：`PASSED`

- [ ] **Step 3: 运行所有测试确保无回归**

```bash
python -m pytest tests/ -v
```

预期输出：所有测试 `PASSED`

- [ ] **Step 4: 在设计文档末尾新增"实现完成"章节**

在 `docs/superpowers/specs/2026-05-20-trend-up-take-profit-design.md` 末尾新增：

```markdown
## 实现完成

- ✅ 新增 TREND_UP 止盈配置常量（config.py）
- ✅ 新增 IndicatorSnapshot.ema_2h_20 字段（context.py）
- ✅ 新增 2H K线构建和 EMA 计算（scheduler.py）
- ✅ sell_signal.py 增加 market_state 分支逻辑
- ✅ 所有测试通过（包括端到端集成测试）

**测试覆盖：**
- 单元测试：`tests/test_sell_signal.py`（14 个测试用例）
- 集成测试：`tests/test_trend_up_integration.py`（1 个端到端流程）
- 回归测试：所有现有测试保持通过
```

- [ ] **Step 5: 提交**

```bash
git add tests/test_trend_up_integration.py docs/superpowers/specs/2026-05-20-trend-up-take-profit-design.md
git commit -m "test: add TREND_UP integration test and update design doc"
```

---

## 自检清单

**Spec 覆盖：**
- ✅ 新增 2H K线和 EMA 指标（Task 2, 3）
- ✅ 新增 TREND_UP 止盈配置（Task 1）
- ✅ sell_signal.py 分支逻辑（Task 4）
- ✅ engine.py 调用更新（Task 5，已验证无需修改）

**占位符扫描：**
- ✅ 无 TBD、TODO、"implement later"
- ✅ 所有代码块完整，无"类似 Task N"引用
- ✅ 所有步骤包含具体命令和预期输出

**类型一致性：**
- ✅ `ema_2h_20` 字段名在所有任务中一致
- ✅ `TREND_TAKE_PROFIT_1_PCT` 等常量名在所有任务中一致
- ✅ `check_sell_signal` 函数签名在所有调用处一致
