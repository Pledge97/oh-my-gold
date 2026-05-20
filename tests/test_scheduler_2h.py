# tests/test_scheduler_2h.py
from backend.data.kline import build_kline

# 二小时K线周期秒数
TWO_HOUR_PERIOD_SEC = 7200

# 毫秒换算常量
MS_PER_SECOND = 1000

# 四小时秒级 tick 数量
FOUR_HOUR_TICK_COUNT = 14400

# 测试价格基准
BASE_TEST_PRICE = 1000.0

# 测试价格循环长度
PRICE_CYCLE = 100

# 测试价格步长
PRICE_STEP = 0.1

# 预期 2H K线数量
EXPECTED_TWO_HOUR_KLINE_COUNT = 2


def test_2h_kline_builds_correctly():
    """验证 2H K线构建逻辑，period_sec 应支持 7200 秒。"""
    # ticks：模拟 4 小时的秒级 tick 数据，预期可聚合为 2 根 2H K线
    ticks = [
        {"ts": i * MS_PER_SECOND, "price": BASE_TEST_PRICE + (i % PRICE_CYCLE) * PRICE_STEP}
        for i in range(FOUR_HOUR_TICK_COUNT)
    ]

    # kline_2h：按 7200 秒窗口聚合出的 2H K线
    kline_2h = build_kline(ticks, period_sec=TWO_HOUR_PERIOD_SEC)

    assert len(kline_2h) == EXPECTED_TWO_HOUR_KLINE_COUNT
    assert "open" in kline_2h.columns
    assert "high" in kline_2h.columns
    assert "low" in kline_2h.columns
    assert "close" in kline_2h.columns
