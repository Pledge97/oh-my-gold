"""
积存金交易时间判断：
  - 周一 09:00 ~ 周六 02:30（跨夜连续交易）
  - 中国法定节假日休市
"""
from datetime import datetime, time
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
    else:
        # 周一~周五：09:00 起开市；00:00~02:30 是前一夜盘延续
        in_session = t >= time(9, 0) or t < time(2, 30)

    if not in_session:
        return False

    # 法定节假日检查：用"本交易段归属的交易日"来判断
    # 夜盘 00:00~02:30 归属于前一天的交易日
    if t < time(2, 30):
        from datetime import timedelta
        trade_date = (dt - timedelta(days=1)).date()
    else:
        trade_date = dt.date()

    return chinese_calendar.is_workday(trade_date)
