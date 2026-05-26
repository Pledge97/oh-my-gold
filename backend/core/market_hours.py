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

# 每小时秒数，用于把接口传入的小时数转换为交易秒数。
SECONDS_PER_HOUR = 3600

# 每秒毫秒数，用于毫秒时间戳和秒级步长互转。
MILLISECONDS_PER_SECOND = 1000


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
    
def calc_trading_time_ranges(
    until_ts_ms: int,
    trading_seconds: float,
    step_sec: int = 60,
) -> list[tuple[int, int]]:
    """
    从截止时间向前回溯指定交易秒数，返回按时间升序排列的开市时间段。

    参数：
        until_ts_ms: 截止时间（毫秒时间戳）
        trading_seconds: 需要回溯的累计开市秒数
        step_sec: 采样间隔（秒），默认 60 秒

    返回：
        开市时间段列表，每项为 (start_ts_ms, end_ts_ms)
    """
    if trading_seconds <= 0:
        return []

    # 剩余交易秒数：每遇到一个开市采样区间就扣减对应时长。
    remaining_seconds = trading_seconds
    # 采样步长毫秒数：用于按固定间隔向前移动时间窗口。
    step_ms = step_sec * MILLISECONDS_PER_SECOND
    # 当前回溯位置：从截止时间开始逐步向前移动。
    current_ms = until_ts_ms
    # 反向区间列表：回溯时先收集从近到远的开市小区间。
    reversed_ranges: list[tuple[int, int]] = []

    while remaining_seconds > 0:
        # 区间起点：用于判断当前回溯到的这一段是否属于开市时间。
        interval_start_ms = current_ms - step_ms
        # 区间终点：当前回溯位置就是本段的右边界。
        interval_end_ms = current_ms
        # 区间实际秒数：首个区间可能不是完整 step_sec。
        interval_seconds = min(step_sec, (interval_end_ms - interval_start_ms) / MILLISECONDS_PER_SECOND)
        # 区间起点时间：按北京时间判断是否处于开市时间。
        interval_start_dt = datetime.fromtimestamp(interval_start_ms / MILLISECONDS_PER_SECOND, tz=CST)

        if is_trading_time(interval_start_dt):
            # 纳入秒数：最后一段可能只需要部分采样区间。
            included_seconds = min(interval_seconds, remaining_seconds)
            # 纳入起点：按实际还需要的交易秒数截断最后一段。
            included_start_ms = interval_end_ms - int(included_seconds * MILLISECONDS_PER_SECOND)
            reversed_ranges.append((included_start_ms, interval_end_ms))
            remaining_seconds -= included_seconds

        current_ms = interval_start_ms

    # 正序区间列表：供接口按时间升序查询和返回。
    ordered_ranges = list(reversed(reversed_ranges))
    # 合并区间列表：把连续的分钟级小区间合并成少量 SQL 查询段。
    merged_ranges: list[tuple[int, int]] = []

    for range_start_ms, range_end_ms in ordered_ranges:
        if not merged_ranges:
            merged_ranges.append((range_start_ms, range_end_ms))
            continue

        # 上一段起止：用于判断当前小区间是否与上一段连续。
        previous_start_ms, previous_end_ms = merged_ranges[-1]
        if range_start_ms <= previous_end_ms:
            merged_ranges[-1] = (previous_start_ms, max(previous_end_ms, range_end_ms))
        else:
            merged_ranges.append((range_start_ms, range_end_ms))

    return merged_ranges
