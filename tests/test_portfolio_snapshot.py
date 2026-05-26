# tests/test_portfolio_snapshot.py
"""测试 _portfolio_snapshot 的止盈止损价格显示逻辑。"""
import pytest
from backend.strategy.engine import StrategyEngine
from backend.risk.portfolio import PortfolioPosition
from backend.core.enums import MarketState
from backend import config


def test_next_tp_shows_tp1_when_not_done():
    """TP1 未完成时，next_tp 显示 TP1 触发价。"""
    engine = StrategyEngine()
    engine._portfolio = PortfolioPosition()
    engine._portfolio.buy(1000.0, 50.0)

    ctx = type("Ctx", (), {
        "indicators": type("I", (), {"atr_5m": 5.0, "bb_lower": 990.0})(),
        "market_state": MarketState.OSCILLATION,
        "ts": None,
    })()

    snapshot = engine._portfolio_snapshot(1010.0, engine._portfolio.pnl_pct(1010.0), ctx)

    # TP1 = 1000 × (1 + 0.006) / (1 - 0.004) = 1010.04
    assert snapshot["next_tp"] == pytest.approx(1010.04, abs=0.01)


def test_next_tp_shows_tp2_when_tp1_done():
    """TP1 完成后，next_tp 显示 TP2 触发价。"""
    engine = StrategyEngine()
    engine._portfolio = PortfolioPosition()
    engine._portfolio.buy(1000.0, 50.0)
    engine._portfolio.tp1_done = True

    ctx = type("Ctx", (), {
        "indicators": type("I", (), {"atr_5m": 5.0, "bb_lower": 990.0})(),
        "market_state": MarketState.OSCILLATION,
        "ts": None,
    })()

    snapshot = engine._portfolio_snapshot(1020.0, engine._portfolio.pnl_pct(1020.0), ctx)

    # TP2 = 1000 × (1 + 0.012) / (1 - 0.004) = 1016.06
    assert snapshot["next_tp"] == pytest.approx(1016.06, abs=0.01)


def test_next_tp_none_when_tp2_done():
    """TP2 完成后，next_tp 为 None（追踪止盈无固定价格）。"""
    engine = StrategyEngine()
    engine._portfolio = PortfolioPosition()
    engine._portfolio.buy(1000.0, 50.0)
    engine._portfolio.tp1_done = True
    engine._portfolio.tp2_done = True

    ctx = type("Ctx", (), {
        "indicators": type("I", (), {"atr_5m": 5.0, "bb_lower": 990.0})(),
        "market_state": MarketState.OSCILLATION,
        "ts": None,
    })()

    snapshot = engine._portfolio_snapshot(1030.0, engine._portfolio.pnl_pct(1030.0), ctx)

    assert snapshot["next_tp"] is None


def test_next_stop_shows_half_loss_when_above_threshold():
    """当前盈亏 > -2.5% 时，next_stop 显示减仓50%触发价。"""
    engine = StrategyEngine()
    engine._portfolio = PortfolioPosition()
    engine._portfolio.buy(1000.0, 50.0)

    ctx = type("Ctx", (), {
        "indicators": type("I", (), {"atr_5m": 5.0, "bb_lower": 990.0})(),
        "market_state": MarketState.OSCILLATION,
        "ts": None,
    })()

    # 当前价格 990，盈亏约 -1.4%，大于 -2.5%
    snapshot = engine._portfolio_snapshot(990.0, engine._portfolio.pnl_pct(990.0), ctx)

    # FORCE_HALF_LOSS = 1000 × (1 - 0.025) / (1 - 0.004) = 978.92
    assert snapshot["next_stop"] == pytest.approx(978.92, abs=0.01)


def test_next_stop_shows_clear_loss_when_below_half_threshold():
    """当前盈亏在 -2.5% 和 -3.5% 之间时，next_stop 显示清仓触发价。"""
    engine = StrategyEngine()
    engine._portfolio = PortfolioPosition()
    engine._portfolio.buy(1000.0, 50.0)

    ctx = type("Ctx", (), {
        "indicators": type("I", (), {"atr_5m": 5.0, "bb_lower": 990.0})(),
        "market_state": MarketState.OSCILLATION,
        "ts": None,
    })()

    # 当前价格 970，盈亏约 -3.4%，在 -2.5% 和 -3.5% 之间
    snapshot = engine._portfolio_snapshot(970.0, engine._portfolio.pnl_pct(970.0), ctx)

    # CLEAR_ALL_LOSS = 1000 × (1 - 0.035) / (1 - 0.004) = 968.88
    assert snapshot["next_stop"] == pytest.approx(968.88, abs=0.01)


def test_next_stop_none_when_below_clear_threshold():
    """当前盈亏 <= -3.5% 时，next_stop 为 None（已触发清仓）。"""
    engine = StrategyEngine()
    engine._portfolio = PortfolioPosition()
    engine._portfolio.buy(1000.0, 50.0)

    ctx = type("Ctx", (), {
        "indicators": type("I", (), {"atr_5m": 5.0, "bb_lower": 990.0})(),
        "market_state": MarketState.OSCILLATION,
        "ts": None,
    })()

    # 当前价格 960，盈亏约 -4.4%，低于 -3.5%
    snapshot = engine._portfolio_snapshot(960.0, engine._portfolio.pnl_pct(960.0), ctx)

    assert snapshot["next_stop"] is None


def test_next_tp_uses_trend_up_thresholds():
    """TREND_UP 模式下，TP1/TP2 使用更高的阈值。"""
    engine = StrategyEngine()
    engine._portfolio = PortfolioPosition()
    engine._portfolio.buy(1000.0, 50.0)

    ctx = type("Ctx", (), {
        "indicators": type("I", (), {"atr_5m": 5.0, "bb_lower": 990.0})(),
        "market_state": MarketState.TREND_UP,
        "ts": None,
    })()

    # TP1 未完成：TREND_TAKE_PROFIT_1_PCT = 0.012
    snapshot = engine._portfolio_snapshot(1020.0, engine._portfolio.pnl_pct(1020.0), ctx)
    # TP1 = 1000 × (1 + 0.012) / (1 - 0.004) = 1016.06
    assert snapshot["next_tp"] == pytest.approx(1016.06, abs=0.01)

    # TP1 完成：TREND_TAKE_PROFIT_2_PCT = 0.020
    engine._portfolio.tp1_done = True
    snapshot = engine._portfolio_snapshot(1030.0, engine._portfolio.pnl_pct(1030.0), ctx)
    # TP2 = 1000 × (1 + 0.020) / (1 - 0.004) = 1024.10
    assert snapshot["next_tp"] == pytest.approx(1024.10, abs=0.01)
