# backend/strategy/engine.py
from backend.core.context import MarketContext
from backend.core.enums import ExitReason, MarketState
from backend.core.market_hours import calc_trading_seconds
from backend.risk.portfolio import PortfolioPosition, load_portfolio_from_signals, calc_sell_pnl
from backend.risk.circuit_breaker import CircuitBreaker
from backend.risk.risk_manager import RiskManager
from backend.signals.regime_signal import detect_regime
from backend.signals.buy_signal import check_buy_signal
from backend.signals.sell_signal import check_sell_signal, get_next_tp_price, get_next_stop_price
from backend.signals.exit_signal import check_exit_signal
from backend.db.database import get_conn
from typing import Optional
from backend import config
import time


class StrategyEngine:
    def __init__(self):
        self.cb = CircuitBreaker()
        self.risk = RiskManager()

        # V3 组合仓位（从 signals 恢复）
        self._portfolio: PortfolioPosition = PortfolioPosition()
        self._load_portfolio_v3()  # 从 signals 表恢复 V3 T仓状态

    def on_tick_v2(self, ctx: MarketContext) -> dict:
        """V2 策略主循环：组合仓位管理版"""
        # 1. 更新市场状态
        ctx.market_state = detect_regime(ctx)

        # 2. 熔断检查
        self.cb.check_tick(ctx.price, ctx.prev_price, ctx.price_5m_ago)
        self.cb.check_atr(ctx.indicators.atr_5m, ctx.indicators.atr_daily_mean)

        # 3. 计算T仓整体盈亏率
        pnl_pct = self._portfolio.pnl_pct(ctx.price)

        signal_out = None

        # 4. 止损检查（优先级最高，熔断时也执行）
        exit_sig = check_exit_signal(self._portfolio, ctx.price, ctx)
        if exit_sig:
            signal_out = self._execute_exit_v3(exit_sig, ctx)

        # 5. 止盈检查
        if not self._portfolio.is_empty():
            sell_sig = check_sell_signal(self._portfolio, ctx, current_ts_ms=ctx.ts or 0)
            if sell_sig:
                signal_out = self._execute_sell_v3(sell_sig, ctx)

        # 6. 建仓/加仓检查（熔断中跳过；本 tick 已触发清仓时跳过）
        already_cleared = signal_out is not None and self._portfolio.is_empty()
        if not self.cb.is_active and ctx.ready and not already_cleared:
            buy_sig = check_buy_signal(
                ctx, self._portfolio,
                circuit_breaker_active=self.cb.is_active,
                last_buy_price=self._portfolio.last_buy_price,
            )
            if buy_sig:
                signal_out = self._execute_buy_v3(buy_sig, ctx)

        return {
            "ts": int(time.time() * 1000),
            "price": ctx.price,
            "market_state": ctx.market_state.value,
            "indicators": {
                "adx": ctx.indicators.adx,
                "plus_di": ctx.indicators.plus_di,
                "minus_di": ctx.indicators.minus_di,
                "bb_upper": ctx.indicators.bb_upper,
                "bb_mid": ctx.indicators.bb_mid,
                "bb_lower": ctx.indicators.bb_lower,
                "rsi": ctx.indicators.rsi,
                "atr": ctx.indicators.atr_5m,
            },
            "signal": signal_out,
            "circuit_breaker": {
                "active": self.cb.is_active,
                "level": self.cb.state.level if self.cb.is_active else None,
            },
            "portfolio": self._portfolio_snapshot(ctx.price, pnl_pct, ctx),
        }

    def _portfolio_snapshot(self, price: float, pnl_pct: float, ctx) -> dict:
        """生成 WebSocket portfolio 字段快照，含下次触发节点。"""
        avg_cost = self._portfolio.avg_cost
        atr = max(ctx.indicators.atr_5m, 5.0)  # 最小5元，避免间距过小
        has_position = not self._portfolio.is_empty()

        # 下次买入触发价：空仓用布林下轨，有仓用 last_buy_price - ATR 间距
        if not has_position:
            next_buy = ctx.indicators.bb_lower or None
        elif self._portfolio.total_amount_g < config.T_MAX_AMOUNT_G and atr and self._portfolio.last_buy_price:
            next_buy = round(self._portfolio.last_buy_price - config.ATR_ADD_LOT_MULTIPLIER * atr, 2)
        else:
            next_buy = None  # 满仓

        # 止盈触发价：根据 tp1_done/tp2_done 状态显示下一个未完成的止盈档位
        next_tp = get_next_tp_price(self._portfolio, ctx)

        # 止损触发价：根据当前盈亏显示下一个止损档位
        next_stop = get_next_stop_price(self._portfolio, pnl_pct)

        return {
            "round_counter": self._portfolio.round_counter,
            "total_amount_g": self._portfolio.total_amount_g,
            "avg_cost": avg_cost,
            "pnl_pct": pnl_pct,
            "pnl_yuan": round(price * self._portfolio.total_amount_g * (1 - config.SELL_FEE_RATE) - self._portfolio.total_cost, 2),
            "tp1_done": self._portfolio.tp1_done,
            "tp2_done": self._portfolio.tp2_done,
            "next_buy": next_buy,
            "next_tp": next_tp,
            "next_stop": next_stop,
        }

    def _execute_buy_v3(self, signal, ctx: MarketContext) -> dict:
        """执行建仓/加仓，只写 signals 表。加仓后重置止盈标记。"""
        if self._portfolio.is_empty():
            self._portfolio.round_counter += 1
        self._portfolio.buy(ctx.price, signal.amount_g, ts=ctx.ts)
        # 加仓后重置止盈标记，下一次止盈从 TP1 开始
        self._portfolio.tp1_done = False
        self._portfolio.tp2_done = False
        self._save_signal(ctx, signal.signal_type.value, signal.amount_g, signal.reason)
        return {"type": signal.signal_type.value, "amount_g": signal.amount_g, "reason": signal.reason}

    def _execute_sell_v3(self, signal, ctx: MarketContext) -> dict:
        """执行止盈减仓/清仓，写 signals 并记录 pnl_yuan。"""
        avg_cost = self._portfolio.avg_cost  # 卖出前取均价
        sold_g = (
            self._portfolio.total_amount_g * signal.sell_ratio
            if signal.sell_ratio < 1.0
            else self._portfolio.total_amount_g
        )
        sold_g = round(sold_g, 4)
        pnl_yuan = calc_sell_pnl(sold_g, ctx.price, avg_cost, config.SELL_FEE_RATE)
        self._portfolio.sell(ctx.price, sold_g, ts=ctx.ts)

        if signal.exit_reason == ExitReason.TAKE_PROFIT_1:
            self._portfolio.tp1_done = True
        elif signal.exit_reason == ExitReason.TAKE_PROFIT_2:
            self._portfolio.tp2_done = True

        self._save_signal(ctx, signal.exit_reason.value, sold_g, signal.reason, pnl_yuan=round(pnl_yuan, 2))
        return {"type": signal.exit_reason.value, "amount_g": sold_g, "reason": signal.reason}

    def _execute_exit_v3(self, signal, ctx: MarketContext) -> dict:
        """执行止损减仓/清仓，写 signals 并记录 pnl_yuan。"""
        avg_cost = self._portfolio.avg_cost  # 卖出前取均价
        sold_g = (
            self._portfolio.total_amount_g * signal.sell_ratio
            if signal.sell_ratio < 1.0
            else self._portfolio.total_amount_g
        )
        sold_g = round(sold_g, 4)
        pnl_yuan = calc_sell_pnl(sold_g, ctx.price, avg_cost, config.SELL_FEE_RATE)
        self._portfolio.sell(ctx.price, sold_g, ts=ctx.ts)
        self._save_signal(ctx, signal.exit_reason.value, sold_g, signal.reason, pnl_yuan=round(pnl_yuan, 2))
        return {"type": signal.exit_reason.value, "amount_g": sold_g, "reason": signal.reason}

    def _load_portfolio_v3(self) -> None:
        """服务启动时从 signals 恢复 V3 T仓状态。"""
        with get_conn() as conn:
            self._portfolio = load_portfolio_from_signals(conn)
            # 已完成全清仓的轮次数量作为 round_counter
            row = conn.execute(
                "SELECT COUNT(*) cnt FROM signals WHERE type IN (?,?,?)",
                ("STOP_LOSS_CLEAR", "TREND_CLEAR", "TAKE_PROFIT_TRAILING"),
            ).fetchone()
            self._portfolio.round_counter = row["cnt"] or 0

    def _save_signal(self, ctx: MarketContext, sig_type: str,
                     amount_g: float, reason: str, pnl_yuan: float | None = None) -> None:
        """保存策略信号，卖出信号可记录本次已实现盈亏。"""
        with get_conn() as conn:
            self._save_signal_raw(
                conn=conn,
                ts=ctx.ts or int(time.time() * 1000),
                sig_type=sig_type,
                mode=ctx.market_state.value,
                price=ctx.price,
                amount_g=amount_g,
                reason=reason,
                pnl_yuan=pnl_yuan,
            )

    def _save_signal_raw(self, conn, ts: int, sig_type: str, mode: str, price: float,
                         amount_g: float, reason: str, pnl_yuan: float | None = None) -> None:
        """底层信号写入方法，方便测试直接验证。"""
        conn.execute(
            "INSERT INTO signals (ts, type, mode, price, amount_g, reason, pnl_yuan) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ts, sig_type, mode, price, amount_g, reason, pnl_yuan),
        )

