"""
积存金交易时间判断：
  - 周一 09:00 开市（无隔夜盘）
  - 周二至周五 09:00 开市，次日 02:30 收市（跨夜连续）
  - 周六 00:00~02:30（周五夜盘延续）
  - 周日全天休市
  - 中国法定节假日休市
"""
from datetime import datetime, time, timedelta
import chinese_calendar


def is_trading_time(dt: datetime | None = None) -> bool:
    """返回 True 表示当前处于积存金交易时间内。"""
    if dt is None:
        dt = datetime.now()

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

    # 周二至周五：09:00 之后 或 凌晨 02:30 之前（前一天夜盘延续）
    else:
        in_session = t >= time(9, 0) or t < time(2, 30)

    if not in_session:
        return False

    # 法定节假日检查：夜盘 00:00~02:30 归属于前一天的交易日
    trade_date = (dt - timedelta(days=1)).date() if t < time(2, 30) else dt.date()
    return chinese_calendar.is_workday(trade_date)
