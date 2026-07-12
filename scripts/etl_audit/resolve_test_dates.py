#!/usr/bin/env python3
"""输出 ETL 测试窗口：最近 N 个 SSE 开市日 + 固定报告期。"""

from __future__ import annotations

import argparse
from datetime import datetime

from src.etl.extract.local.stock.stock_trade_calendar_local_extract import (
    TradeCalLocalExtract,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve ETL test date window")
    parser.add_argument("-n", type=int, default=5, help="最近 N 个开市日")
    parser.add_argument(
        "--end-date",
        default=None,
        help="截止日 YYYYMMDD，默认今日",
    )
    args = parser.parse_args()

    end = (args.end_date or datetime.now().strftime("%Y%m%d")).strip()
    dates = TradeCalLocalExtract().get_open_trade_dates(
        start_date="20200101",
        end_date=end,
        exchange="SSE",
    )
    last_n = dates[-args.n :] if len(dates) >= args.n else dates

    print(f"today={end}")
    print(f"last_{args.n}_open_dates={last_n}")
    if last_n:
        print(f"d5={last_n[0]}")
        print(f"d1={last_n[-1]}")
        print(f"test_month={last_n[-1][:6]}")
    print("periods=['20251231', '20260331']")


if __name__ == "__main__":
    main()
