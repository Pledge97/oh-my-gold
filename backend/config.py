import os

# 资金配置
BASE_POSITION_G = 50.0  # 底仓目标克数，用于长期持有仓位规划
T_POSITION_G = 100.0  # T仓目标最大克数，用于短线策略仓位规划
CASH_G_EQUIV = 50.0  # 预留现金折算克数，用于资金占用评估

# 交易成本
SELL_FEE_RATE = 0.004  # 卖出手续费率，用于计算扣费后盈亏

# 市场状态
ADX_TREND_THRESHOLD = 25.0  # ADX 趋势判定阈值，高于该值倾向判定为趋势行情
ADX_LOOKBACK = 3  # ADX 连续观察周期数，用于降低市场状态抖动

# 指标参数
BB_PERIOD = 20  # 布林带计算周期
BB_STD = 2.0  # 布林带标准差倍数
RSI_PERIOD = 14  # RSI 计算周期
ATR_PERIOD = 14  # ATR 计算周期
ADX_PERIOD = 14  # ADX 计算周期
EMA_SHORT = 20  # 短周期 EMA 参数
EMA_LONG = 60  # 长周期 EMA 参数

# 趋势模式
TREND_RSI_OVERSOLD = 40  # TREND_UP 空仓回调建仓的 RSI 超卖阈值

# 熔断
CB1_TICK_PCT = 0.005  # 一级熔断 5 秒涨跌幅阈值
CB1_TICK_PAUSE_MIN = 10  # 一级熔断 5 秒异常波动暂停分钟数
CB1_5MIN_PCT = 0.015  # 一级熔断 5 分钟涨跌幅阈值
CB1_5MIN_PAUSE_MIN = 30  # 一级熔断 5 分钟异常波动暂停分钟数
CB2_ATR_MULT = 3.0  # 二级熔断 ATR 相对日均 ATR 的倍数阈值
CB3_DAILY_STOP_COUNT = 3  # 三级熔断单日止损次数阈值
CB_LONG_PAUSE_HOURS = 24  # 二级和三级熔断触发后的暂停小时数

# 数据源
AKSHARE_SYMBOL = "Au99.99"  # AkShare 日线行情品种代码
JDJYGOLD_URL = "https://api.jdjygold.com/gw2/generic/jrm/h5/m/stdLatestPrice"  # 京东金融积存金实时价格接口
JDJYGOLD_SKU = "1961543816"  # 京东金融积存金商品 SKU
TICK_INTERVAL_SEC = 5  # 实时价格采集间隔秒数

# 数据库
DB_PATH = "data/gold.db"  # SQLite 数据库文件路径

# PushPlus 微信提醒
PUSHPLUS_BATCH_SEND_URL = "http://www.pushplus.plus/batchSend"  # PushPlus 多渠道发送接口地址
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN", "2febfc5b33e949319215ae85764f2f43")  # PushPlus 用户令牌
PUSHPLUS_TOPIC = os.getenv("PUSHPLUS_TOPIC", "oh-my-gold")  # PushPlus 群组编码
PUSHPLUS_TEMPLATE = os.getenv("PUSHPLUS_TEMPLATE", "html")  # PushPlus 消息模板
PUSHPLUS_CHANNEL = os.getenv("PUSHPLUS_CHANNEL", "wechat")  # PushPlus 发送渠道
PUSHPLUS_OPTION = os.getenv("PUSHPLUS_OPTION", "")  # PushPlus 渠道配置编码，微信渠道无需配置
PUSHPLUS_TIMEOUT_SEC = 5.0  # PushPlus 请求超时时间

# ── 组合仓位管理（V2） ──────────────────────────────────────
# 分批建仓量（克）
LOT1_AMOUNT_G: float = 50.0   # 第1批：初始开仓
LOT2_AMOUNT_G: float = 30.0   # 第2批：加仓
LOT3_AMOUNT_G: float = 20.0   # 第3批：加仓
T_MAX_AMOUNT_G: float = 100.0  # T仓最大持仓量

# 加仓触发间距（ATR₁₄ 的倍数）
ATR_ADD_LOT_MULTIPLIER: float = 1.0  # 加仓触发所需的价格下跌 ATR 倍数

# 布林下轨买入缓冲：避免价格刚贴近下轨就建仓
BB_LOWER_BUY_BUFFER_ATR_MULTIPLIER: float = 0.2  # 布林下轨买入缓冲 ATR 倍数
BB_LOWER_BUY_MIN_BUFFER: float = 0.5  # 布林下轨买入最小缓冲价差（元/克）

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

# 卖出后重新买入冷却
REENTRY_COOLDOWN_SECONDS: int = 30 * 60       # 止盈/止损卖出后，默认30分钟内不按近似价格买回
REENTRY_PRICE_GAP_ATR_MULTIPLIER: float = 2.0 # 冷却期内价格至少继续下跌2个ATR才允许提前买回
REENTRY_MIN_PRICE_GAP: float = 10.0            # 提前买回的最小价格间距（元/克）
FULL_CLEAR_REENTRY_COOLDOWN_SECONDS: int = 12 * 60 * 60       # 清仓后，默认12小时内不按近似价格买回
FULL_CLEAR_REENTRY_PRICE_GAP_ATR_MULTIPLIER: float = 3.0       # 清仓冷却期内价格至少继续下跌3个ATR才允许提前买回
FULL_CLEAR_REENTRY_MIN_PRICE_GAP: float = 20.0                 # 清仓后提前买回的最小价格间距（元/克）
