"""回测报告落盘。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl


def write_backtest_output(
    out_dir: Path,
    *,
    portfolio: pl.DataFrame,
    trades: pl.DataFrame,
    returns: pl.DataFrame,
    ic: pl.DataFrame,
    summary: dict[str, Any],
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    if not portfolio.is_empty():
        portfolio.write_parquet(out_dir / "portfolio.parquet")
    else:
        pl.DataFrame(
            schema={
                "trade_date": pl.Utf8,
                "group_id": pl.Utf8,
                "ts_code": pl.Utf8,
                "weight": pl.Float64,
            }
        ).write_parquet(out_dir / "portfolio.parquet")

    if not trades.is_empty():
        trades.write_parquet(out_dir / "trades.parquet")
    else:
        pl.DataFrame(
            schema={
                "trade_date": pl.Utf8,
                "group_id": pl.Utf8,
                "ts_code": pl.Utf8,
                "delta_weight": pl.Float64,
                "cost": pl.Float64,
            }
        ).write_parquet(out_dir / "trades.parquet")

    returns.write_parquet(out_dir / "returns.parquet")
    ic.write_parquet(out_dir / "ic.parquet")

    report_path = out_dir / "report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=_json_default)

    return out_dir


def _json_default(obj: Any) -> Any:
    if isinstance(obj, float):
        return obj
    return str(obj)


def print_summary(summary: dict[str, Any]) -> None:
    print("── 回测摘要 ──")
    for k in (
        "strategy",
        "factor",
        "start",
        "end",
        "rebalance",
        "groups",
        "run_id",
        "ic_mean",
        "rank_ic_mean",
        "icir",
        "sharpe",
        "annual_return",
        "mdd",
        "avg_turnover",
        "output_dir",
    ):
        if k in summary:
            print(f"  {k}: {summary[k]}")
