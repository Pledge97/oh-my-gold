# backend/strategy/engine.py
from backend.core.context import MarketContext
from backend.core.enums import CloseType, ExitReason
from backend.risk.position import PositionManager, Position, PortfolioPosition
from backend.risk.circuit_breaker import CircuitBreaker
from backend.risk.risk_manager import RiskManager
from backend.signals.regime_signal import detect_regime
from backend.signals.buy_signal import check_buy, check_buy_signal
from backend.signals.sell_signal import check_sell, check_sell_signal
from backend.signals.exit_signal import check_exit, check_exit_signal
from backend.db.database import get_conn
from typing import Optional
from backend import config
import time


class StrategyEngine:
    def __init__(self):
        self.positions = PositionManager()
        self.cb = CircuitBreaker()
        self.risk = RiskManager()
        self._open_positions: list[Position] = []
        self._last_stop_loss_ts: int = 0
        self._last_buy_ts: int = 0
        self._last_buy_price: float = 0.0
        self._last_take_profit_ts: int = 0
        self._STOP_LOSS_COOLDOWN_MS = 5 * 60 * 1000    # 止损后5分钟不开仓
        self._BUY_COOLDOWN_MS = 5 * 60 * 1000           # 每次买入后5分钟内不再买
        self._TAKE_PROFIT_COOLDOWN_MS = 5 * 60 * 1000  # 止盈后5分钟内不再止盈

        # V2 组合仓位
        self._portfolio: PortfolioPosition = PortfolioPosition(round_id=0)
        self._v2_last_buy_price: Optional[float] = None  # 上次买入价，用于加仓间距判断
        self._v2_round_counter: int = 0                   # 自增轮次ID
        self._load_portfolio_v2()  # 从数据库恢复未平仓的V2持仓

    def on_tick(self, ctx: MarketContext) -> dict:
        # 1. 更新市场状态
        ctx.market_state = detect_regime(ctx)

        # 2. 熔断检查
        self.cb.check_tick(ctx.price, ctx.prev_price, ctx.price_5m_ago)
        self.cb.check_atr(ctx.indicators.atr_5m, ctx.indicators.atr_daily_mean)

        # 3. 检查已有持仓止盈/止损（熔断时也执行）
        closed = []
        now_ms = int(time.time() * 1000)
        in_tp_cooldown = (now_ms - self._last_take_profit_ts) < self._TAKE_PROFIT_COOLDOWN_MS

        for pos in self._open_positions:
            pos.peak_price = max(pos.peak_price, ctx.price)

            # 止损：立即执行，不受冷却限制
            exit_sig = check_exit(ctx, pos.open_price, pos.peak_price)
            if exit_sig.triggered:
                is_trend_exit = "趋势转跌" in exit_sig.reason
                close_type = CloseType.TAKE_PROFIT if is_trend_exit else CloseType.STOP_LOSS
                pnl = self.positions.close(pos, ctx.price, close_type)
                self.risk.record_pnl(pnl["pnl_yuan"], ctx.price)
                if not is_trend_exit:
                    self.cb.on_stop_loss()
                    self._last_stop_loss_ts = ctx.ts if ctx.ts else now_ms
                else:
                    self._last_take_profit_ts = now_ms
                sig_label = "TAKE_PROFIT" if is_trend_exit else "STOP_LOSS"
                self._save_signal(ctx, sig_label, pos.amount_g, exit_sig.reason)
                closed.append(pos)
                continue

            # 止盈：冷却期内跳过，避免连续卖出
            if in_tp_cooldown:
                continue

            sell_sig = check_sell(ctx, pos.open_price, pos.peak_price)
            if sell_sig.triggered:
                pnl = self.positions.close(pos, ctx.price, CloseType.TAKE_PROFIT)
                self.risk.record_pnl(pnl["pnl_yuan"], ctx.price)
                self._save_signal(ctx, "TAKE_PROFIT", pos.amount_g, sell_sig.reason)
                closed.append(pos)
                self._last_take_profit_ts = now_ms
                in_tp_cooldown = True  # 本 tick 内只止盈一笔

        for pos in closed:
            self._open_positions.remove(pos)

        signal_out = None

        # 4. 开仓信号（熔断、风控暂停、冷却期内跳过）
        in_sl_cooldown = (now_ms - self._last_stop_loss_ts) < self._STOP_LOSS_COOLDOWN_MS
        in_buy_cooldown = (now_ms - self._last_buy_ts) < self._BUY_COOLDOWN_MS

        # 有持仓时，加仓要求价格比上次开仓再低至少1个ATR
        atr = ctx.indicators.atr_5m or 3.0
        price_far_enough = (
            len(self._open_positions) == 0
            or ctx.price <= self._last_buy_price - atr
        )

        if (not self.cb.is_active and self.risk.can_trade() and ctx.ready
                and not in_sl_cooldown and not in_buy_cooldown and price_far_enough):
            unit_g = self.risk.unit_buy_g()
            buy_sig = check_buy(ctx, len(self._open_positions), unit_g)
            if buy_sig.triggered:
                pos = self.positions.open(ctx.price, buy_sig.amount_g)
                self._open_positions.append(pos)
                self._last_buy_ts = now_ms
                self._last_buy_price = ctx.price
                self._save_signal(ctx, "BUY", buy_sig.amount_g, buy_sig.reason)
                signal_out = {"type": "BUY", "amount_g": buy_sig.amount_g,
                              "reason": buy_sig.reason}

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
            "positions": [
                {
                    "id": pos.id,
                    "open_price": pos.open_price,
                    "amount_g": pos.amount_g,
                    "pnl_pct": round((ctx.price - pos.open_price) / pos.open_price, 6),
                    "pnl_yuan": round(
                        (ctx.price - pos.open_price) * pos.amount_g
                        - ctx.price * pos.amount_g * 0.004,
                        2,
                    ),
                }
                for pos in self._open_positions
            ],
        }

    def _save_signal(self, ctx: MarketContext, sig_type: str,
                     amount_g: float, reason: str) -> None:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO signals (ts, type, mode, price, amount_g, reason) VALUES (?,?,?,?,?,?)",
                (int(time.time() * 1000), sig_type, ctx.market_state.value,
                 ctx.price, amount_g, reason),
            )

    # ── V2 组合仓位方法 ────────────────────────────────────────

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
            signal_out = self._execute_exit_v2(exit_sig, ctx)

        # 5. 止盈检查
        if not self._portfolio.is_empty():
            sell_sig = check_sell_signal(self._portfolio, ctx)
            if sell_sig:
                signal_out = self._execute_sell_v2(sell_sig, ctx)

        # 6. 建仓/加仓检查（熔断中跳过；本 tick 已触发清仓时跳过）
        already_cleared = signal_out is not None and self._portfolio.is_empty()
        if not self.cb.is_active and ctx.ready and not already_cleared:
            buy_sig = check_buy_signal(
                ctx, self._portfolio,
                circuit_breaker_active=self.cb.is_active,
                last_buy_price=self._v2_last_buy_price,
            )
            if buy_sig:
                signal_out = self._execute_buy_v2(buy_sig, ctx)

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
            "portfolio": self._portfolio_snapshot(ctx.price, pnl_pct),
        }

    def _portfolio_snapshot(self, price: float, pnl_pct: float) -> dict:
        """生成 portfolio 字段的 dict 快照"""
        return {
            "round_id": self._portfolio.round_id,
            "total_amount_g": self._portfolio.total_amount_g,
            "total_cost": self._portfolio.total_cost,
            "avg_cost": self._portfolio.avg_cost,
            "pnl_pct": pnl_pct,
            "pnl_yuan": round(
                price * self._portfolio.total_amount_g - self._portfolio.total_cost, 2
            ),
            "tp1_done": self._portfolio.tp1_done,
            "tp2_done": self._portfolio.tp2_done,
            "lots": [
                {
                    "lot_index": lot.lot_index,
                    "open_price": lot.open_price,
                    "amount_g": lot.amount_g,
                    "open_ts": lot.open_ts,
                    "status": lot.status.value,
                }
                for lot in self._portfolio.lots
                if lot.status.value == "OPEN"
            ],
        }

    def _execute_buy_v2(self, signal, ctx: MarketContext) -> dict:
        """执行建仓/加仓"""
        ts = ctx.ts or int(time.time() * 1000)

        if self._portfolio.is_empty():
            self._v2_round_counter += 1
            self._portfolio = PortfolioPosition(round_id=self._v2_round_counter)
            self._save_position_open_v2(ts, ctx.price, signal.amount_g)

        lot = self._portfolio.add_lot(
            lot_index=self._portfolio.lot_count,
            price=ctx.price,
            amount_g=signal.amount_g,
            ts=ts,
        )
        self._v2_last_buy_price = ctx.price
        self._save_lot_v2(lot)
        # 加仓后同步更新 positions 表总持仓量（初始建仓时已在 INSERT 中写入，无需重复）
        if self._portfolio.lot_count > 1:
            self._update_position_amount_v2()
        self._save_signal(ctx, signal.signal_type.value, signal.amount_g, signal.reason)
        return {"type": signal.signal_type.value, "amount_g": signal.amount_g,
                "reason": signal.reason}

    def _execute_sell_v2(self, signal, ctx: MarketContext) -> dict:
        """执行止盈减仓/清仓"""
        ts = ctx.ts or int(time.time() * 1000)
        # 在 clear/reduce 之前捕获持仓数据用于 PnL 计算
        pre_amount_g = self._portfolio.total_amount_g
        pre_cost = self._portfolio.total_cost

        if signal.sell_ratio >= 1.0:
            sold_g = self._portfolio.clear(ctx.price, ts)
        else:
            sold_g = self._portfolio.reduce(signal.sell_ratio, ctx.price, ts)

        if signal.exit_reason == ExitReason.TAKE_PROFIT_1:
            self._portfolio.mark_tp1()
        elif signal.exit_reason == ExitReason.TAKE_PROFIT_2:
            self._portfolio.mark_tp2()

        self._save_signal(ctx, signal.exit_reason.value, sold_g, signal.reason)
        if self._portfolio.is_empty():
            self._save_position_close_v2(ctx.price, ts, signal.exit_reason.value,
                                         pre_amount_g, pre_cost)
            self._v2_last_buy_price = None
        return {"type": signal.exit_reason.value, "amount_g": sold_g, "reason": signal.reason}

    def _execute_exit_v2(self, signal, ctx: MarketContext) -> dict:
        """执行止损减仓/清仓"""
        ts = ctx.ts or int(time.time() * 1000)
        # 在 clear/reduce 之前捕获持仓数据用于 PnL 计算
        pre_amount_g = self._portfolio.total_amount_g
        pre_cost = self._portfolio.total_cost

        if signal.sell_ratio >= 1.0:
            sold_g = self._portfolio.clear(ctx.price, ts)
        else:
            sold_g = self._portfolio.reduce(signal.sell_ratio, ctx.price, ts)

        self._save_signal(ctx, signal.exit_reason.value, sold_g, signal.reason)
        if self._portfolio.is_empty():
            self._save_position_close_v2(ctx.price, ts, signal.exit_reason.value,
                                         pre_amount_g, pre_cost)
            self._v2_last_buy_price = None
        return {"type": signal.exit_reason.value, "amount_g": sold_g, "reason": signal.reason}

    def _load_portfolio_v2(self) -> None:
        """服务启动时从数据库恢复未平仓的V2持仓状态"""
        with get_conn() as conn:
            # 找最新的V2持仓：position_lots 表中有对应 round_id 的 OPEN positions
            row = conn.execute("""
                SELECT p.id, p.open_ts FROM positions p
                WHERE p.status = 'OPEN'
                  AND EXISTS (SELECT 1 FROM position_lots l WHERE l.round_id = p.id)
                ORDER BY p.open_ts DESC LIMIT 1
            """).fetchone()
            if not row:
                return

            round_id = row['id']
            self._v2_round_counter = round_id

            lots = conn.execute("""
                SELECT lot_index, open_price, amount_g, open_ts
                FROM position_lots
                WHERE round_id = ? AND status = 'OPEN'
                ORDER BY open_ts ASC
            """, (round_id,)).fetchall()

        if not lots:
            return

        self._portfolio = PortfolioPosition(round_id=round_id)
        for lot in lots:
            self._portfolio.add_lot(
                lot_index=lot['lot_index'],
                price=lot['open_price'],
                amount_g=lot['amount_g'],
                ts=lot['open_ts'],
            )
        # 恢复上次买入价（最后一批的买入价，用于加仓间距判断）
        self._v2_last_buy_price = lots[-1]['open_price']

    def _save_position_open_v2(self, ts: int, open_price: float, amount_g: float) -> None:
        """在 positions 表创建新轮次记录，写入第1批的真实价格和克数"""
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO positions (open_ts, open_price, amount_g, status) VALUES (?, ?, ?, 'OPEN')",
                (ts, open_price, amount_g),
            )
            self._portfolio.round_id = cur.lastrowid

    def _update_position_amount_v2(self) -> None:
        """加仓后同步更新 positions 表的总持仓量"""
        with get_conn() as conn:
            conn.execute(
                "UPDATE positions SET amount_g=? WHERE id=?",
                (self._portfolio.total_amount_g, self._portfolio.round_id),
            )

    def _save_lot_v2(self, lot) -> None:
        """在 position_lots 表记录批次买入"""
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO position_lots
                   (round_id, lot_index, open_ts, open_price, amount_g, status)
                   VALUES (?, ?, ?, ?, ?, 'OPEN')""",
                (self._portfolio.round_id, lot.lot_index,
                 lot.open_ts, lot.open_price, lot.amount_g),
            )

    def _save_position_close_v2(self, price: float, ts: int, reason: str,
                                 total_amount_g: float, total_cost: float) -> None:
        """更新 positions 表关闭本轮记录（接收预计算的持仓量和成本）"""
        fee = price * total_amount_g * config.SELL_FEE_RATE
        pnl_yuan = price * total_amount_g - total_cost - fee
        pnl_g = pnl_yuan / price if price > 0 else 0.0
        with get_conn() as conn:
            conn.execute(
                """UPDATE positions SET status='CLOSED', close_ts=?, pnl_yuan=?,
                   pnl_g=?, close_type=? WHERE id=?""",
                (ts, round(pnl_yuan, 2), round(pnl_g, 4),
                 reason, self._portfolio.round_id),
            )
