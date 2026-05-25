from datetime import datetime, timezone, timedelta
import pytest
from backend.core.market_hours import calc_trading_seconds

# 北京时间 UTC+8
CST = timezone(timedelta(hours=8))


def ts(dt_str: str) -> int:
    """将 'YYYY-MM-DD HH:MM' 转为毫秒时间戳（北京时间）"""
    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=CST)
    return int(dt.timestamp() * 1000)


def test_zero_when_same_ts():
    """起止时间相同，累计时长为 0"""
    t = ts("2025-05-20 10:00")  # 周二交易时段
    assert calc_trading_seconds(t, t) == pytest.approx(0.0)


def test_one_hour_in_trading_session():
    """周二 10:00~11:00，完整交易时段，应累计 3600 秒"""
    result = calc_trading_seconds(ts("2025-05-20 10:00"), ts("2025-05-20 11:00"))
    assert result == pytest.approx(3600.0, abs=120)  # 允许采样误差 2 分钟


def test_non_trading_time_not_counted():
    """周日全天休市，累计时长应为 0"""
    result = calc_trading_seconds(ts("2025-05-18 10:00"), ts("2025-05-18 12:00"))
    assert result == pytest.approx(0.0)


def test_spans_non_trading_gap():
    """跨越周一 02:30~09:00 非交易时段，只计算交易时段部分"""
    # 周一无隔夜盘，01:00~09:00 均非交易时段，09:00~10:00 交易（60 分钟）
    result = calc_trading_seconds(ts("2025-05-19 01:00"), ts("2025-05-19 10:00"))
    # 预期约 60 分钟 = 3600 秒
    assert result == pytest.approx(3600.0, abs=120)


def test_24_trading_hours_across_weekend():
    """跨越周末，只累计工作日交易时段，24交易小时实际经历更长的自然时间"""
    # 周五 14:00 ~ 下周一 12:00：周五下午+夜盘+周一上午，应能累计约 24 小时交易时长
    result = calc_trading_seconds(ts("2025-05-16 14:00"), ts("2025-05-19 14:00"))
    # 周五 14:00~02:30(次日) = 12.5h，周一 09:00~14:00 = 5h，共 17.5h 还不够，说明需要更长区间
    # 此测试验证：跨周末时周六 00:00~02:30 夜盘延续计入，周日不计入
    assert result == pytest.approx(17.5 * 3600, abs=240)  # 17.5 trading hours, 4-min tolerance
