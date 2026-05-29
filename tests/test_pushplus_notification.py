import httpx
import pytest

from backend.core.enums import MarketState


def test_build_signal_message_content_uses_panel_label():
    """验证交易信号通知正文使用前端信号面板一致的类型文案。"""
    from backend.notifications.pushplus import build_signal_message_content

    content = build_signal_message_content(
        sig_type="TAKE_PROFIT_1",
        price=723.456,
        amount_g=12.3456,
        pnl_yuan=88.8,
        reason="达到第一档止盈",
    )

    assert content == "当前金价￥723.46，触发了1轮止盈，克数：12.3456 g，盈亏：￥88.80，原因：达到第一档止盈。"


def test_build_buy_message_content_omits_pnl():
    """验证建仓通知正文不展示盈亏字段。"""
    from backend.notifications.pushplus import build_signal_message_content

    content = build_signal_message_content(
        sig_type="BUY",
        price=723.456,
        amount_g=50.0,
        pnl_yuan=None,
        reason="达到建仓条件",
    )

    assert content == "当前金价￥723.46，触发了建仓，克数：50 g，原因：达到建仓条件。"


def test_build_add_lot_message_content_omits_pnl():
    """验证加仓通知正文不展示盈亏字段。"""
    from backend.notifications.pushplus import build_signal_message_content

    content = build_signal_message_content(
        sig_type="ADD_LOT",
        price=723.456,
        amount_g=30.0,
        pnl_yuan=None,
        reason="达到加仓条件",
    )

    assert content == "当前金价￥723.46，触发了加仓，克数：30 g，原因：达到加仓条件。"


def test_build_circuit_breaker_message_content_omits_amount_and_pnl():
    """验证熔断通知正文只展示金价、信号类型和原因。"""
    from backend.notifications.pushplus import build_circuit_breaker_message_content

    content = build_circuit_breaker_message_content(
        level=2,
        price=725.0,
        reason="ATR异常",
    )

    assert content == "当前金价￥725.00，触发了二级熔断，原因：ATR异常。"


def test_send_pushplus_message_posts_batch_send_payload(monkeypatch):
    """验证 PushPlus 多渠道接口请求参数符合微信渠道配置。"""
    from backend.notifications import pushplus

    posted = {}

    def fake_post(url, json, timeout):
        """记录请求参数并返回成功响应。"""
        posted["url"] = url
        posted["json"] = json
        posted["timeout"] = timeout
        return httpx.Response(
            200,
            json={"code": 200, "msg": "执行成功", "data": []},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(pushplus.httpx, "post", fake_post)

    ok = pushplus.send_pushplus_message("测试标题", "测试内容")

    assert ok is True
    assert posted["url"] == "http://www.pushplus.plus/batchSend"
    assert posted["json"] == {
        "token": "2febfc5b33e949319215ae85764f2f43",
        "title": "测试标题",
        "content": "测试内容",
        "topic": "oh-my-gold",
        "template": "html",
        "channel": "wechat",
        "option": "",
    }


def test_send_signal_notice_uses_price_type_and_amount_title(monkeypatch):
    """验证交易信号标题包含当前金价、类型文案和克数。"""
    from backend.notifications import pushplus

    sent = {}

    def fake_send_pushplus_message(title, content):
        """记录 PushPlus 标题和正文。"""
        sent["title"] = title
        sent["content"] = content
        return True

    monkeypatch.setattr(pushplus, "send_pushplus_message", fake_send_pushplus_message)

    ok = pushplus.send_signal_notice(
        sig_type="ADD_LOT",
        price=723.456,
        amount_g=30.0,
        pnl_yuan=None,
        reason="测试加仓",
    )

    assert ok is True
    assert sent["title"] == "金价:723.46 加仓"


def test_send_circuit_breaker_notice_uses_price_and_type_title(monkeypatch):
    """验证熔断标题包含当前金价和类型文案。"""
    from backend.notifications import pushplus

    sent = {}

    def fake_send_pushplus_message(title, content):
        """记录 PushPlus 标题和正文。"""
        sent["title"] = title
        sent["content"] = content
        return True

    monkeypatch.setattr(pushplus, "send_pushplus_message", fake_send_pushplus_message)

    ok = pushplus.send_circuit_breaker_notice(
        level=3,
        price=723.456,
        reason="测试三级熔断",
    )

    assert ok is True
    assert sent["title"] == "金价:723.46 三级熔断"


def test_strategy_save_signal_sends_wechat_notice(tmp_path, monkeypatch):
    """验证交易信号落库后会触发微信通知。"""
    import backend.db.database as db_mod
    import backend.strategy.engine as engine_mod
    from backend.db.database import init_db
    from backend.strategy.engine import StrategyEngine

    sent = []

    def fake_send_signal_notice(sig_type, price, amount_g, pnl_yuan, reason):
        """记录交易信号通知参数。"""
        sent.append((sig_type, price, amount_g, pnl_yuan, reason))
        return True

    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(engine_mod, "send_signal_notice", fake_send_signal_notice)
    init_db()

    engine = StrategyEngine()
    ctx = type("Ctx", (), {"ts": 1000, "price": 721.2, "market_state": MarketState.OSCILLATION})()
    engine._save_signal(ctx, "BUY", 50.0, "测试建仓")

    assert sent == [("BUY", 721.2, 50.0, None, "测试建仓")]


def test_circuit_breaker_activation_sends_wechat_notice(tmp_path, monkeypatch):
    """验证熔断激活后会触发微信通知。"""
    import backend.db.database as db_mod
    import backend.risk.circuit_breaker as cb_mod
    from backend.db.database import init_db
    from backend.risk.circuit_breaker import CircuitBreaker

    sent = []

    def fake_send_circuit_breaker_notice(level, price, reason):
        """记录熔断通知参数。"""
        sent.append((level, price, reason))
        return True

    monkeypatch.setattr(db_mod, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(cb_mod, "send_circuit_breaker_notice", fake_send_circuit_breaker_notice)
    init_db()

    cb = CircuitBreaker()
    cb.check_tick(price=1006.0, prev_price=1000.0, price_5m_ago=1000.0)

    assert sent == [(1, 1006.0, "5秒涨跌幅=0.600%")]
