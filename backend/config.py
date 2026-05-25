# 资金配置
BASE_POSITION_G = 50.0
T_POSITION_G = 100.0
CASH_G_EQUIV = 50.0

# 交易成本
SELL_FEE_RATE = 0.004
MIN_PROFIT_RATE = 0.006

# 单次开仓
UNIT_BUY_G = 20.0
MAX_ADD_COUNT = 3

# 市场状态
ADX_TREND_THRESHOLD = 25.0
ADX_LOOKBACK = 3

# 指标参数
BB_PERIOD = 20
BB_STD = 2.0
RSI_PERIOD = 14
ATR_PERIOD = 14
ADX_PERIOD = 14
EMA_SHORT = 20
EMA_LONG = 60

# 震荡模式
OSC_TAKE_PROFIT_RATE = 0.006
OSC_ADD_ATR_MULT = 1.5
OSC_STOP_LOSS_ATR_MULT = 2.0

# 趋势模式
TREND_STOP_LOSS_ATR_MULT = 2.0
TREND_STOP_LOSS_FIXED = 0.015
TREND_MIN_PROFIT = 0.008
TREND_RSI_OVERSOLD = 40
TREND_DECAY_TRAIL = 0.005

# 风控
DAILY_LOSS_LIMIT_RATE = 0.03
SINGLE_STOP_LOSS_RATE = 0.015
CONSECUTIVE_LOSS_DAYS = 3
REDUCED_UNIT_BUY_G = 10.0

# 熔断
CB1_TICK_PCT = 0.005
CB1_TICK_PAUSE_MIN = 10
CB1_5MIN_PCT = 0.015
CB1_5MIN_PAUSE_MIN = 30
CB2_ATR_MULT = 3.0
CB3_DAILY_STOP_COUNT = 3
CB3_CONSEC_DAYS = 3
CB3_CONSEC_STOP_PER_DAY = 2

# 数据源
AKSHARE_SYMBOL = "Au99.99"
JDJYGOLD_URL = "https://api.jdjygold.com/gw2/generic/jrm/h5/m/stdLatestPrice"
JDJYGOLD_SKU = "1961543816"
TICK_INTERVAL_SEC = 5

# 数据库
DB_PATH = "data/gold.db"

# ── 组合仓位管理（V2） ──────────────────────────────────────
# 分批建仓量（克）
LOT1_AMOUNT_G: float = 50.0   # 第1批：初始开仓
LOT2_AMOUNT_G: float = 30.0   # 第2批：加仓
LOT3_AMOUNT_G: float = 20.0   # 第3批：加仓
T_MAX_AMOUNT_G: float = 100.0  # T仓最大持仓量

# 加仓触发间距（ATR₁₄ 的倍数）
ATR_ADD_LOT_MULTIPLIER: float = 1.0

# 组合止损阈值（负数表示亏损）
STOP_ADD_LOSS_PCT: float = -0.015   # 浮亏超过此值停止加仓
FORCE_HALF_LOSS_PCT: float = -0.025  # 浮亏超过此值强制减仓50%
CLEAR_ALL_LOSS_PCT: float = -0.035   # 浮亏超过此值全部清仓

# 组合止盈阈值
TAKE_PROFIT_1_PCT: float = 0.006   # 第1次止盈触发盈利率
TAKE_PROFIT_2_PCT: float = 0.012   # 第2次止盈触发盈利率
TAKE_PROFIT_1_SELL_RATIO: float = 0.60  # 第1次止盈卖出比例
TAKE_PROFIT_2_SELL_RATIO: float = 0.20  # 第2次止盈卖出比例

# TREND_UP 专属止盈阈值
TREND_TAKE_PROFIT_1_PCT: float = 0.012  # TREND_UP 第1次止盈触发盈利率
TREND_TAKE_PROFIT_2_PCT: float = 0.020  # TREND_UP 第2次止盈触发盈利率
TREND_TP1_SELL_RATIO: float = 0.40      # TREND_UP 第1次止盈卖出比例
TREND_TP2_SELL_RATIO: float = 0.30      # TREND_UP 第2次止盈卖出初始仓位比例

# 满仓超时降低止盈
FULL_POSITION_TIMEOUT_HOURS: float = 24.0     # 满仓超时阈值（交易小时）
FULL_POSITION_TIMEOUT_TP1_PCT: float = 0.003  # 超时后降低的 TP1 止盈率（0.3%）
