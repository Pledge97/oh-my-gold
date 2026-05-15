# 黄金积存金做T量化系统 — 系统设计文档

**日期：** 2026-05-14
**版本：** v1.0
**技术栈：** FastAPI + React + SQLite

---

## 一、整体架构

```
┌─────────────────────────────────────────┐
│              React 前端                  │
│  实时价格图 | 信号面板 | 持仓表 | 绩效统计  │
└──────────────┬──────────────────────────┘
               │ WebSocket（实时推送，5秒）
               │ REST API（查询/操作）
┌──────────────▼──────────────────────────┐
│              FastAPI 后端                │
│                                         │
│  ┌──────────┐  ┌──────────┐  ┌───────┐  │
│  │ 数据采集  │  │ 策略引擎  │  │ 风控  │  │
│  │ (5秒轮询) │  │(信号计算) │  │熔断器 │  │
│  └──────────┘  └──────────┘  └───────┘  │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │           SQLite                  │   │
│  │ 价格历史 | 信号记录 | 持仓 | 绩效  │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
               │
        ┌──────▼──────┐
        │  行情数据源   │
        │  jdjygold   │
        │  akshare    │
        └─────────────┘
```

---

## 二、数据源

| 数据源 | 用途 | 更新频率 |
|--------|------|---------|
| `akshare` AU9999 日线 | 历史日K，计算ADX/日线指标 | 启动时拉取，每日更新一次 |
| `akshare` AU9999 实时价格 | 策略引擎信号源（过渡阶段） | 5秒轮询 |
| `jdjygold` 实时接口 | 后台静默采集积存金tick数据 | 5秒轮询 |

**过渡策略：**
- 当前：策略引擎使用 `akshare` AU9999 实时价格运行，同时后台静默采集 `jdjygold` tick数据
- 切换条件：`jdjygold` tick数据积累 ≥ 7天后，将策略引擎数据源切换为 `jdjygold`
- 两者价格高度相关，策略逻辑无需修改，只需切换数据源

**jdjygold接口：**
```
GET https://api.jdjygold.com/gw2/generic/jrm/h5/m/stdLatestPrice?productSku=1961543816

响应示例：
{
    "resultData": {
        "datas": {
            "price": "1025.73",          // 当前金价（元/g）
            "yesterdayPrice": "1028.53", // 昨日收盘价
            "upAndDownAmt": "-2.80",     // 涨跌额
            "upAndDownRate": "-0.27%",   // 涨跌幅
            "time": "1778749537000",     // 毫秒时间戳
            "productSku": "1961543816",
            "id": 47921661
        },
        "status": "SUCCESS"
    },
    "success": true,
    "resultCode": 0
}

采集字段：resultData.datas.price（元/g），resultData.datas.time（毫秒时间戳）
```

---

## 三、后端目录结构

```
backend/
├── main.py                     # FastAPI入口，启动调度器和WebSocket
├── config.py                   # 所有可调参数（阈值、周期等）
├── core/
│   ├── event_bus.py            # 事件总线：发布/订阅 TickEvent / KlineEvent / SignalEvent
│   ├── scheduler.py            # 调度器：驱动5秒tick，触发事件
│   ├── context.py              # 运行上下文：持有当前K线、指标快照，回测/实盘共用
│   └── enums.py                # 全局枚举：MarketState, SignalType, CloseType, Mode
├── data/
│   ├── fetch_history.py        # 已完成：akshare历史日K采集
│   ├── fetcher_tick.py         # akshare实时价格5秒轮询（实盘数据源）
│   └── kline.py                # 纯函数：tick列表 → OHLC DataFrame，不读数据库
├── indicators/                 # 纯函数层，只做 calculate(df) → value，不读数据库
│   ├── adx.py                  # calc_adx(df, period) → dict
│   ├── bollinger.py            # calc_bollinger(df, period, std) → dict
│   ├── rsi.py                  # calc_rsi(df, period) → float
│   ├── atr.py                  # calc_atr(df, period) → float
│   └── ema.py                  # calc_ema(df, period) → Series
├── signals/                    # 信号层：输入指标快照，输出 SignalEvent，不含仓位逻辑
│   ├── regime_signal.py        # 市场状态：基于ADX斜率判断 OSCILLATION/TREND_UP/TREND_DOWN/DECAY
│   ├── buy_signal.py           # 买入信号：初始开仓50g（布林下轨）+ 加仓30g/20g（每跌1×ATR）
│   ├── sell_signal.py          # 止盈信号：T仓盈利0.6%卖60%，1.2%卖20%，EMA跌破清仓
│   └── exit_signal.py          # 止损信号：T仓浮亏-1.5%停加仓，-2.5%减半，-3.5%清仓
├── strategy/
│   └── engine.py               # 纯调度器：on_tick()，计算T仓整体盈亏，协调信号层与风控层
├── risk/
│   ├── circuit_breaker.py      # 三级熔断器（含ATR波动熔断，阈值1.8倍均值）
│   ├── position.py             # 组合持仓管理：统一计算T仓整体成本/浮盈/浮亏
│   └── risk_manager.py         # 日内风控（日亏上限/连续亏损降仓）
├── db/
│   ├── database.py             # 已完成：SQLite连接/初始化
│   └── models.py               # 表结构常量
└── api/
    ├── routes.py               # REST接口
    └── websocket.py            # WebSocket推送
```

### 数据流

```
scheduler.py（5秒触发）
    │
    ▼
fetcher_tick.py → 获取实时价格
    │
    ▼
event_bus.py → 发布 TickEvent
    │
    ▼
context.py → 更新K线快照（调用 kline.py 纯函数）
           → 更新指标快照（调用 indicators/ 纯函数）
    │
    ▼
signals/ → 读取 context 指标快照 → 生成 SignalEvent
    │
    ▼
engine.py on_signal() → 检查 risk/ → 决定执行
    │
    ▼
position.py → 更新持仓 → websocket.py → 推送前端
```

**回测复用：** 只需替换 `scheduler.py`（改为历史数据回放），`signals/`、`indicators/`、`risk/` 完全不动。

---

## 四、数据库设计

### daily_prices（日线历史，来自akshare）
```sql
CREATE TABLE daily_prices (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    date   TEXT NOT NULL UNIQUE,
    open   REAL NOT NULL,
    high   REAL NOT NULL,
    low    REAL NOT NULL,
    close  REAL NOT NULL,
    volume REAL
);
```

### prices（tick数据，来自jdjygold）
```sql
CREATE TABLE prices (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    ts    INTEGER NOT NULL,
    price REAL NOT NULL
);
CREATE INDEX idx_prices_ts ON prices(ts);
```

### signals（信号记录）
```sql
CREATE TABLE signals (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        INTEGER NOT NULL,
    type      TEXT NOT NULL,   -- BUY / SELL / STOP_LOSS
    mode      TEXT NOT NULL,   -- OSCILLATION / TREND
    price     REAL NOT NULL,
    amount_g  REAL NOT NULL,
    reason    TEXT
);
```

### positions（持仓记录）
```sql
CREATE TABLE positions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    open_ts     INTEGER NOT NULL,
    open_price  REAL NOT NULL,
    amount_g    REAL NOT NULL,
    add_count   INTEGER DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'OPEN',  -- OPEN / CLOSED
    close_ts    INTEGER,
    close_price REAL,
    close_type  TEXT,   -- TAKE_PROFIT / STOP_LOSS
    pnl_yuan    REAL,   -- 盈亏（元），已扣手续费
    pnl_g       REAL    -- 盈亏（g）
);
```

### circuit_breaker_logs（熔断日志）
```sql
CREATE TABLE circuit_breaker_logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_ts    INTEGER NOT NULL,
    level         INTEGER NOT NULL,  -- 1 / 2 / 3
    reason        TEXT NOT NULL,
    trigger_value REAL,
    resume_ts     INTEGER
);
```

---

## 五、WebSocket 推送格式

每5秒推送一次，前端订阅后实时更新：

```json
{
  "ts": 1778746766000,
  "price": 1027.96,
  "market_state": "OSCILLATION",
  "indicators": {
    "adx": 18.5,
    "plus_di": 22.1,
    "minus_di": 19.3,
    "bb_upper": 1031.2,
    "bb_mid": 1026.8,
    "bb_lower": 1022.4,
    "rsi": 38.5,
    "atr": 3.2
  },
  "signal": {
    "type": "BUY",
    "amount_g": 20,
    "reason": "价格触及布林下轨，RSI=38.5"
  },
  "circuit_breaker": {
    "active": false,
    "level": null,
    "resume_ts": null
  },
  "positions": [
    {
      "id": 1,
      "open_price": 1024.5,
      "amount_g": 20,
      "pnl_pct": 0.33,
      "pnl_yuan": 6.8
    }
  ]
}
```

---

## 六、REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/signals?limit=50` | 历史信号列表 |
| GET | `/api/positions?status=OPEN` | 持仓列表 |
| GET | `/api/performance` | 绩效统计汇总 |
| GET | `/api/circuit-breaker` | 熔断状态和日志 |
| GET | `/api/prices/daily?days=30` | 日K数据（图表用） |
| POST | `/api/circuit-breaker/resume` | 手动解除三级熔断 |

---

## 七、前端目录结构

```
frontend/
├── src/
│   ├── components/
│   │   ├── PriceChart.tsx          # 实时价格K线图（lightweight-charts）
│   │   ├── SignalPanel.tsx         # 信号记录列表
│   │   ├── PositionTable.tsx       # 当前持仓表
│   │   ├── PerformanceStats.tsx    # 绩效统计卡片
│   │   └── CircuitBreakerBadge.tsx # 熔断状态指示器
│   ├── hooks/
│   │   └── useWebSocket.ts         # WebSocket连接管理
│   ├── store/
│   │   └── useStore.ts             # Zustand全局状态
│   ├── types/
│   │   └── index.ts                # TypeScript类型定义
│   └── App.tsx                     # 主布局
├── index.html
├── vite.config.ts
└── package.json
```

### 页面布局

```
┌─────────────────────────────────────────────────────┐
│  顶部状态栏：当前金价 | 市场状态 | 熔断状态 | 持仓盈亏  │
├──────────────────────┬──────────────────────────────┤
│                      │  信号面板                     │
│   实时价格K线图        │  时间 | 类型 | 价格 | 克数    │
│   + 布林带/EMA叠加    │  原因                        │
│                      ├──────────────────────────────┤
│                      │  当前持仓                     │
│                      │  开仓价 | 克数 | 盈亏% | 状态  │
├──────────────────────┴──────────────────────────────┤
│  绩效统计：总收益 | 胜率 | 盈亏比 | 最大回撤 | 交易次数 │
└─────────────────────────────────────────────────────┘
```

### 前端依赖

| 用途 | 库 |
|------|-----|
| 框架 | React 18 + TypeScript |
| 构建 | Vite |
| K线图 | lightweight-charts |
| UI组件 | Ant Design |
| 实时数据 | 原生 WebSocket |
| 状态管理 | Zustand |

---

## 八、开发阶段规划

| 阶段 | 内容 | 前提条件 |
|------|------|---------|
| 阶段一（当前） | 数据采集：jdjygold tick + akshare日K | 已完成 |
| 阶段二 | 后端核心：K线合成 + 指标计算 + 策略引擎 | tick数据 ≥ 7天 |
| 阶段三 | 风控模块：熔断器 + 持仓管理 + 日内风控 | 阶段二完成 |
| 阶段四 | API + WebSocket | 阶段三完成 |
| 阶段五 | 前端 React 界面 | 阶段四完成 |
| 阶段六 | 模拟交易验证 + 绩效统计 | 阶段五完成 |
