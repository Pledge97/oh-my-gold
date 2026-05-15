# backend/strategy/engine.py
from backend.core.context import MarketContext
from backend.core.enums import CloseType
from backend.risk.position import PositionManager, Position
from backend.risk.circuit_breaker import CircuitBreaker
from backend.risk.risk_manager import RiskManager
from backend.signals.regime_signal import detect_regime
from backend.signals.buy_signal import check_buy
from backend.signals.sell_signal import check_sell
from backend.signals.exit_signal import check_exit
from backend.db.database import get_conn
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
        self._STOP_LOSS_COOLDOWN_MS = 5 * 60 * 1000   # 止损后5分钟不开仓
        self._BUY_COOLDOWN_MS = 15 * 60 * 1000         # 每次买入后15分钟内不再买

    def on_tick(self, ctx: MarketContext) -> dict:
        # 1. 更新市场状态
        ctx.market_state = detect_regime(ctx)

        # 2. 熔断检查
        self.cb.check_tick(ctx.price, ctx.prev_price, ctx.price_5m_ago)
        self.cb.check_atr(ctx.indicators.atr_5m, ctx.indicators.atr_daily_mean)

        # 3. 检查已有持仓止盈/止损（熔断时也执行）
        closed = []
        for pos in self._open_positions:
            pos.peak_price = max(pos.peak_price, ctx.price)

            exit_sig = check_exit(ctx, pos.open_price, pos.peak_price)
            if exit_sig.triggered:
                is_trend_exit = "趋势转跌" in exit_sig.reason
                close_type = CloseType.TAKE_PROFIT if is_trend_exit else CloseType.STOP_LOSS
                pnl = self.positions.close(pos, ctx.price, close_type)
                self.risk.record_pnl(pnl["pnl_yuan"], ctx.price)
                if not is_trend_exit:
                    self.cb.on_stop_loss()
                    self._last_stop_loss_ts = ctx.ts if ctx.ts else int(time.time() * 1000)
                sig_label = "TAKE_PROFIT" if is_trend_exit else "STOP_LOSS"
                self._save_signal(ctx, sig_label, pos.amount_g, exit_sig.reason)
                closed.append(pos)
                continue

            sell_sig = check_sell(ctx, pos.open_price, pos.peak_price)
            if sell_sig.triggered:
                pnl = self.positions.close(pos, ctx.price, CloseType.TAKE_PROFIT)
                self.risk.record_pnl(pnl["pnl_yuan"], ctx.price)
                self._save_signal(ctx, "TAKE_PROFIT", pos.amount_g, sell_sig.reason)
                closed.append(pos)

        for pos in closed:
            self._open_positions.remove(pos)

        signal_out = None

        # 4. 开仓信号（熔断、风控暂停、冷却期内跳过）
        now_ms = int(time.time() * 1000)
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
