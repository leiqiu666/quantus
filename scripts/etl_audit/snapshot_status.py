#!/usr/bin/env python3
"""按 source_name + 窗口打印 completeness_snapshot below 95% 的 date_key。"""

from __future__ import annotations

import argparse

from src.common.completeness import CompletenessConfig, CompletenessEngine
from src.common.function import MACRO_COMPLETE_THRESHOLD
from src.entities.data_entities.completeness_snapshot_entities import (
    CompletenessSnapshotEntities,
)
from src.common.database import Database


def _scan_raw(source: str, start: str | None, end: str | None) -> list[tuple[str, int, int, float]]:
    db = Database()
    session = db.get_session()
    try:
        q = session.query(CompletenessSnapshotEntities).filter_by(source_name=source)
        if start:
            q = q.filter(CompletenessSnapshotEntities.date_key >= start)
        if end:
            q = q.filter(CompletenessSnapshotEntities.date_key <= end)
        rows = q.order_by(CompletenessSnapshotEntities.date_key).all()
        out = []
        for r in rows:
            if not r.period_stock_count:
                continue
            ratio = r.resolved_count / r.period_stock_count
            if ratio < MACRO_COMPLETE_THRESHOLD:
                out.append((r.date_key, r.resolved_count, r.period_stock_count, ratio))
        return out
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="completeness source_name")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--threshold", type=float, default=MACRO_COMPLETE_THRESHOLD)
    args = parser.parse_args()

    below = _scan_raw(args.source, args.start, args.end)
    if not below:
        print(f"[{args.source}] 全部达标 (≥{args.threshold:.0%})")
        return
    print(f"[{args.source}] {len(below)} 个缺口 (<{args.threshold:.0%}):")
    for dk, resolved, expected, ratio in below[:20]:
        print(f"  {dk}  {resolved}/{expected}  ({ratio:.1%})")
    if len(below) > 20:
        print(f"  ... 共 {len(below)} 条")


if __name__ == "__main__":
    main()
