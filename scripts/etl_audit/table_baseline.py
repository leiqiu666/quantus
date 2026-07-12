#!/usr/bin/env python3
"""测试表 COUNT / min-max 日期基线。"""

from __future__ import annotations

import argparse

from sqlalchemy import func, text

from src.common.database import Database

# table -> date column (None = 仅 COUNT)
TABLES: dict[str, str | None] = {
    "stock_list": None,
    "stock_trade_calendar": "cal_date",
    "stock_suspend": "trade_date",
    "kline_daily": "trade_date",
    "market_daily_basic": "trade_date",
    "market_dividend": "record_date",
    "kline_stock_factor": "trade_date",
    "market_moneyflow": "trade_date",
    "market_margin_detail": "trade_date",
    "market_northbound_top10": "trade_date",
    "financial_stock_holder": "ann_date",
    "index_weight": "trade_date",
    "market_dragon_tiger_list": "trade_date",
    "market_dragon_tiger_inst": "trade_date",
    "market_block_trade": "trade_date",
    "financial_shareholder_top10": "ann_date",
    "financial_forecast": "end_date",
    "financial_express": "end_date",
    "financial_audit": "end_date",
    "financial_report_income": "end_date",
    "financial_report_balance": "end_date",
    "financial_report_cashflow": "end_date",
    "financial_report_indicator": "end_date",
    "completeness_snapshot": "date_key",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tables",
        nargs="*",
        default=None,
        help="表名列表，默认全部",
    )
    parser.add_argument("--window-start", default=None, help="窗口起点（date 列过滤）")
    parser.add_argument("--window-end", default=None, help="窗口终点")
    args = parser.parse_args()

    names = args.tables or list(TABLES.keys())
    db = Database()
    session = db.get_session()
    try:
        for name in names:
            col = TABLES.get(name)
            if col is None:
                cnt = session.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar()
                print(f"{name}\tcount={cnt}")
                continue
            base = f"SELECT COUNT(*), MIN({col}), MAX({col}) FROM {name}"
            params: dict = {}
            if args.window_start and args.window_end:
                base += f" WHERE {col} >= :s AND {col} <= :e"
                params = {"s": args.window_start, "e": args.window_end}
            row = session.execute(text(base), params).one()
            label = ""
            if args.window_start:
                label = f" window={args.window_start}~{args.window_end}"
            print(f"{name}{label}\tcount={row[0]}\tmin={row[1]}\tmax={row[2]}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
