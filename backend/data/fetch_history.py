"""
采集 akshare AU9999 近3年日K数据，存入 daily_prices 表。
用法：python -m backend.data.fetch_history
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.db.database import get_conn, init_db


def fetch_and_store():
    try:
        import akshare as ak
    except ImportError:
        print("请先安装 akshare：pip install akshare")
        sys.exit(1)

    init_db()

    three_years_ago = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # 最新数据在昨天或今天则跳过
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) cnt, MAX(date) max_date FROM daily_prices WHERE date >= ?",
            (three_years_ago,)
        ).fetchone()
    if row["cnt"] > 0 and row["max_date"] and row["max_date"] >= yesterday:
        print(f"日K数据已是最新（{row['cnt']}条，最新至{row['max_date']}），跳过拉取")
        return

    print("正在从 akshare 拉取 AU9999 历史日K数据...")
    df = ak.spot_hist_sge(symbol="Au99.99")
    df = df[df["date"].astype(str) >= three_years_ago].copy()
    df = df.sort_values("date").reset_index(drop=True)

    if df.empty:
        print("未获取到数据，请检查 akshare 接口")
        sys.exit(1)

    rows = [
        (
            str(row["date"])[:10],
            float(row["open"]),
            float(row["high"]),
            float(row["low"]),
            float(row["close"]),
            float(row["volume"]) if "volume" in row and row["volume"] else None,
        )
        for _, row in df.iterrows()
    ]

    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO daily_prices (date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                open   = excluded.open,
                high   = excluded.high,
                low    = excluded.low,
                close  = excluded.close,
                volume = excluded.volume
            """,
            rows,
        )

    print(f"完成：共写入 {len(rows)} 条日K数据（{rows[0][0]} 至 {rows[-1][0]}）")


if __name__ == "__main__":
    fetch_and_store()
