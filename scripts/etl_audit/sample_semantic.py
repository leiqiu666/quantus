#!/usr/bin/env python3
"""指定表+日期抽样本行，打印关键字段（供人工/Tushare 比对）。"""

from __future__ import annotations

import argparse
import json

from sqlalchemy import text

from src.common.database import Database

PRESETS: dict[str, dict] = {
    "market_daily_basic": {
        "date_col": "trade_date",
        "cols": "ts_code,trade_date,close,pe,pb,total_mv",
    },
    "kline_daily": {
        "date_col": "trade_date",
        "cols": "ts_code,trade_date,open,high,low,close,vol,up_limit,down_limit",
    },
    "market_moneyflow": {
        "date_col": "trade_date",
        "cols": "ts_code,trade_date,buy_sm_amount,sell_sm_amount,net_mf_amount",
    },
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True, choices=list(PRESETS.keys()))
    parser.add_argument("--date", required=True, help="YYYYMMDD")
    parser.add_argument("-n", type=int, default=3, help="样本行数")
    args = parser.parse_args()

    preset = PRESETS[args.table]
    dc = preset["date_col"]
    cols = preset["cols"]
    sql = text(
        f"SELECT {cols} FROM {args.table} "
        f"WHERE {dc} = :d ORDER BY ts_code LIMIT :n"
    )
    db = Database()
    session = db.get_session()
    try:
        rows = session.execute(sql, {"d": args.date, "n": args.n}).mappings().all()
        print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2, default=str))
    finally:
        session.close()


if __name__ == "__main__":
    main()
