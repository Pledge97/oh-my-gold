import pytest


@pytest.fixture(autouse=True)
def disable_external_pushplus_requests(request, monkeypatch):
    """除 PushPlus 专项测试外，默认屏蔽真实微信提醒请求。"""
    if request.node.path.name == "test_pushplus_notification.py":
        return

    try:
        from backend.notifications import pushplus
    except ModuleNotFoundError:
        return

    monkeypatch.setattr(pushplus, "send_pushplus_message", lambda title, content: True)
