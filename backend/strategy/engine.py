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
                pnl = self.positions.close(pos, ctx.price, CloseType.STOP_LOSS)
                self.risk.record_pnl(pnl["pnl_yuan"], ctx.price)
                self.cb.on_stop_loss()
                self._save_signal(ctx, "STOP_LOSS", pos.amount_g, exit_sig.reason)
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

        # 4. 开仓信号（熔断或风控暂停时跳过）
        if not self.cb.is_active and self.risk.can_trade() and ctx.ready:
            unit_g = self.risk.unit_buy_g()
            buy_sig = check_buy(ctx, len(self._open_positions), unit_g)
            if buy_sig.triggered:
                pos = self.positions.open(ctx.price, buy_sig.amount_g)
                self._open_positions.append(pos)
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
