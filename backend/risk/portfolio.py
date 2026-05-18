from __future__ import annotations

from dataclasses import dataclass
from sqlite3 import Connection, Row

from backend import config

# 信号类型分类常量
BUY_TYPES = ("BUY", "ADD_LOT")
PARTIAL_SELL_TYPES = ("TAKE_PROFIT_1", "TAKE_PROFIT_2", "STOP_LOSS_HALF")
FULL_CLEAR_TYPES = ("STOP_LOSS_CLEAR", "TREND_CLEAR", "TAKE_PROFIT_TRAILING")
SELL_TYPES = PARTIAL_SELL_TYPES + FULL_CLEAR_TYPES


@dataclass
class PortfolioPosition:
    """
    V3 T仓内存状态，所有字段均可从 signals 推导。
    不再维护 lots 列表和 round_id，简化为纯状态容器。
    """
    round_counter: int = 0                  # 当前轮次计数器（保留用于未来扩展）
    total_amount_g: float = 0.0             # 当前持仓总克数
    total_cost: float = 0.0                 # 当前持仓总成本（元）
    tp1_done: bool = False                  # 第1次止盈是否已执行
    tp2_done: bool = False                  # 第2次止盈是否已执行
    realized_pnl: float = 0.0               # 累计已实现盈亏（元，扣除手续费）
    last_buy_price: float | None = None     # 最近一次买入价格（用于加仓判断）

    @property
    def avg_cost(self) -> float:
        """返回当前持仓均价（元/克）。"""
        if self.total_amount_g == 0:
            return 0.0
        return self.total_cost / self.total_amount_g

    def is_empty(self) -> bool:
        """判断当前 T 仓是否为空。"""
        return self.total_amount_g <= 0

    def pnl_pct(self, current_price: float) -> float:
        """计算扣除卖出手续费后的浮动盈亏率。"""
        if self.total_cost == 0:
            return 0.0
        market_value = current_price * self.total_amount_g
        fee = market_value * config.SELL_FEE_RATE
        return (market_value - fee - self.total_cost) / self.total_cost

    def buy(self, price: float, amount_g: float) -> None:
        """
        记录买入或加仓后的内存状态。
        更新持仓量、成本和最近买入价。
        """
        self.total_amount_g += amount_g
        self.total_cost += price * amount_g
        self.last_buy_price = price

    def sell(self, price: float, amount_g: float) -> float:
        """
        按当前均价卖出指定克数，返回本次实现盈亏（用于实时交易，不用于回放）。
        回放时应使用存储的 pnl_yuan，避免重复计算。
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
        return pnl_yuan


def calc_sell_pnl(sold_g: float, sell_price: float, avg_cost: float, fee_rate: float) -> float:
    """
    计算单次卖出已实现盈亏（扣除手续费）。

    参数:
        sold_g: 卖出克数
        sell_price: 卖出价格（元/克）
        avg_cost: 持仓均价（元/克）
        fee_rate: 卖出手续费率

    返回:
        已实现盈亏（元）
    """
    revenue = sell_price * sold_g
    cost = avg_cost * sold_g
    fee = revenue * fee_rate
    return revenue - cost - fee


def get_current_round_signals(conn: Connection) -> list[Row]:
    """
    读取最近一次全清仓之后的当前轮次信号。

    参数:
        conn: 数据库连接

    返回:
        当前轮次的信号列表（按时间升序）
    """
    last_clear = conn.execute(
        "SELECT MAX(ts) ts FROM signals WHERE type IN (?,?,?)",
        FULL_CLEAR_TYPES,
    ).fetchone()
    since_ts = last_clear["ts"] if last_clear and last_clear["ts"] is not None else 0
    return conn.execute(
        "SELECT * FROM signals WHERE ts > ? ORDER BY ts ASC",
        (since_ts,),
    ).fetchall()


def load_portfolio_from_signals(conn: Connection) -> PortfolioPosition:
    """
    从当前轮次 signals 重建 V3 T 仓状态。
    回放时使用存储的 pnl_yuan，不重新计算。

    参数:
        conn: 数据库连接

    返回:
        重建的 PortfolioPosition 对象
    """
    rows = get_current_round_signals(conn)
    portfolio = PortfolioPosition()
    for row in rows:
        sig_type = row["type"]
        amount_g = float(row["amount_g"])
        price = float(row["price"])
        if sig_type in BUY_TYPES:
            portfolio.buy(price, amount_g)
        elif sig_type in SELL_TYPES:
            # 回放时不调用 sell()（会重新计算盈亏），直接用存储的 pnl_yuan
            sold_g = min(amount_g, portfolio.total_amount_g)
            avg = portfolio.avg_cost
            portfolio.total_amount_g = round(portfolio.total_amount_g - sold_g, 4)
            portfolio.total_cost = round(max(portfolio.total_cost - avg * sold_g, 0.0), 4)
            if row["pnl_yuan"] is not None:
                portfolio.realized_pnl = round(portfolio.realized_pnl + float(row["pnl_yuan"]), 4)
        if sig_type == "TAKE_PROFIT_1":
            portfolio.tp1_done = True
        if sig_type == "TAKE_PROFIT_2":
            portfolio.tp2_done = True
    return portfolio

