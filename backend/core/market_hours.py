"""
积存金交易时间判断：
  - 周一 09:00 开市（无隔夜盘）
  - 周二至周五 09:00 开市，次日 02:30 收市（跨夜连续）
  - 周六 00:00~02:30（周五夜盘延续）
  - 周日全天休市
  - 中国法定节假日休市
"""
from datetime import datetime, time, timedelta, timezone
import chinese_calendar

# 北京时间 UTC+8
CST = timezone(timedelta(hours=8))


def is_trading_time(dt: datetime | None = None) -> bool:
    """返回 True 表示当前处于积存金交易时间内。"""
    if dt is None:
        dt = datetime.now(CST)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=CST)

    weekday = dt.weekday()  # 0=周一 … 6=周日
    t = dt.time()

    # 周日全天休市
    if weekday == 6:
        return False

    # 周六：只有 00:00~02:30 是交易时间（周五夜盘延续）
    if weekday == 5:
        in_session = t < time(2, 30)

    # 周一：无隔夜盘，仅 09:00 之后开市
    elif weekday == 0:
        in_session = t >= time(9, 0)

    # 周二至周五：全天 24 小时开市
    else:
        in_session = True

    if not in_session:
        return False

    # 法定节假日检查：夜盘 00:00~02:30 归属于前一天的交易日
    trade_date = (dt - timedelta(days=1)).date() if t < time(2, 30) else dt.date()
    return chinese_calendar.is_workday(trade_date)


def calc_trading_seconds(since_ts_ms: int, until_ts_ms: int, step_sec: int = 60) -> float:
    """
    计算从 since_ts_ms 到 until_ts_ms 之间累计处于交易时段内的秒数。
    按 step_sec 步长采样，每个采样点若处于交易时段则计入 step_sec 秒。

    参数：
        since_ts_ms: 起始时间（毫秒时间戳）
        until_ts_ms: 截止时间（毫秒时间戳）
        step_sec: 采样间隔（秒），默认 60 秒

    返回：
        累计交易时长（秒）
    """
    if until_ts_ms <= since_ts_ms:
        return 0.0

    total = 0.0
    step_ms = step_sec * 1000
    current_ms = since_ts_ms

    while current_ms < until_ts_ms:
        dt = datetime.fromtimestamp(current_ms / 1000, tz=CST)
        if is_trading_time(dt):
            # 最后一个采样点可能不足一个完整步长
            remaining_ms = until_ts_ms - current_ms
            total += min(step_sec, remaining_ms / 1000)
        current_ms += step_ms

    return total
