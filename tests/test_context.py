# tests/test_context.py
from backend.core.context import IndicatorSnapshot


def test_indicator_snapshot_has_ema_2h_20():
    """IndicatorSnapshot 应包含 ema_2h_20 字段，默认值为 0.0。"""
    # 指标快照：使用默认参数创建，验证新增字段的默认行为
    snapshot = IndicatorSnapshot()

    assert hasattr(snapshot, "ema_2h_20")
    assert snapshot.ema_2h_20 == 0.0
