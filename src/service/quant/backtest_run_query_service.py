"""回测运行查询 Service。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import polars as pl

from src.common.setting import settings
from src.model.kline.backtest_run_model import BacktestRunModel
from src.research.performance.returns import calc_returns_metrics

BENCHMARK_CODE = "000300.SH"


def _row_to_list_item(row) -> dict[str, Any]:
    summary = row.summary_json if isinstance(row.summary_json, dict) else {}
    return {
        "run_id": row.run_id,
        "backtest_mode": row.backtest_mode,
        "factor_name": row.factor_name,
        "combo_id": row.combo_id,
        "combo_name": row.combo_name,
        "start_date": row.start_date,
        "end_date": row.end_date,
        "rebalance": row.rebalance,
        "groups": row.groups,
        "status": row.status,
        "ic_mean": summary.get("ic_mean"),
        "rank_ic_mean": summary.get("rank_ic_mean"),
        "sharpe": summary.get("sharpe"),
        "annual_return": summary.get("annual_return"),
        "mdd": summary.get("mdd"),
        "output_dir": row.output_dir,
        "error_message": row.error_message,
        "created_at": row.created_at.isoformat(sep=" ", timespec="seconds")
        if row.created_at
        else None,
    }


def _read_parquet_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        df = pl.read_parquet(path)
    except Exception:
        return []
    if df.is_empty():
        return []
    return df.to_dicts()


def _cum_nav(returns: list[dict[str, Any]], col: str) -> list[dict[str, Any]]:
    """日收益 → 累计净值曲线点。"""
    nav = 1.0
    out: list[dict[str, Any]] = []
    for row in returns:
        r = row.get(col)
        if r is None:
            continue
        try:
            nav *= 1.0 + float(r)
        except (TypeError, ValueError):
            continue
        out.append({"trade_date": row.get("trade_date"), "value": nav})
    return out


def _group_cols(returns_rows: list[dict[str, Any]]) -> list[str]:
    if not returns_rows:
        return []
    return sorted(
        [
            c
            for c in returns_rows[0].keys()
            if isinstance(c, str) and c.startswith("G") and c[1:].isdigit()
        ],
        key=lambda x: int(x[1:]),
    )


def _group_totals(returns_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for g in _group_cols(returns_rows):
        nav = 1.0
        for row in returns_rows:
            r = row.get(g)
            if r is None:
                continue
            try:
                nav *= 1.0 + float(r)
            except (TypeError, ValueError):
                continue
        out.append(
            {
                "group_id": g,
                "total_return": nav - 1.0,
                "final_nav": nav,
            }
        )
    return out


def _yearly_metrics(returns_rows: list[dict[str, Any]], col: str = "long_short") -> list[dict]:
    by_year: dict[str, list[float]] = {}
    for row in returns_rows:
        td = row.get("trade_date")
        r = row.get(col)
        if not td or r is None:
            continue
        try:
            by_year.setdefault(str(td)[:4], []).append(float(r))
        except (TypeError, ValueError):
            continue
    out: list[dict[str, Any]] = []
    for year in sorted(by_year.keys()):
        m = calc_returns_metrics(by_year[year])
        out.append(
            {
                "year": year,
                "annual_return": m.get("annual_return"),
                "sharpe": m.get("sharpe"),
                "mdd": m.get("mdd"),
                "n_days": len(by_year[year]),
            }
        )
    return out


def _load_benchmark_nav(
    start: str, end: str, trade_dates: list[str]
) -> list[dict[str, Any]]:
    """基准累计净值（对齐回测交易日，起点=1）。"""
    closes = _load_index_closes(start, end)
    if not closes:
        return []
    dates = trade_dates or sorted(closes.keys())
    # 找到起点前最近收盘作为基准
    base: float | None = None
    for d in sorted(closes.keys()):
        if d <= (dates[0] if dates else start):
            base = closes[d]
        if dates and d >= dates[0]:
            break
    if base is None or base == 0:
        # 用区间内第一个有值的收盘
        for d in dates:
            if d in closes and closes[d]:
                base = closes[d]
                break
    if base is None or base == 0:
        return []

    out: list[dict[str, Any]] = []
    last = base
    for d in dates:
        if d in closes and closes[d]:
            last = closes[d]
        out.append({"trade_date": d, "value": last / base})
    return out


def _load_index_closes(start: str, end: str) -> dict[str, float]:
    root = Path(settings.warehouse_root) / "index_daily"
    if root.exists():
        try:
            df = (
                pl.scan_parquet(str(root / "**" / "*.parquet"))
                .filter(
                    (pl.col("ts_code") == BENCHMARK_CODE)
                    & (pl.col("trade_date") >= start)
                    & (pl.col("trade_date") <= end)
                )
                .select("trade_date", "close")
                .collect()
            )
            if not df.is_empty():
                return {
                    str(r["trade_date"]): float(r["close"])
                    for r in df.iter_rows(named=True)
                    if r.get("close") is not None
                }
        except Exception:
            pass
    try:
        from src.common.database import Database
        from src.entities.data_entities.index.index_daily_entities import (
            IndexDailyEntities,
        )

        session = Database().get_session()
        try:
            rows = (
                session.query(IndexDailyEntities.trade_date, IndexDailyEntities.close)
                .filter(
                    IndexDailyEntities.ts_code == BENCHMARK_CODE,
                    IndexDailyEntities.trade_date >= start,
                    IndexDailyEntities.trade_date <= end,
                )
                .all()
            )
        finally:
            session.close()
        return {
            str(r[0]): float(r[1]) for r in rows if r[0] is not None and r[1] is not None
        }
    except Exception:
        return {}


def _align_excess(
    ls_nav: list[dict[str, Any]], bm_nav: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    bm_map = {p["trade_date"]: p["value"] for p in bm_nav if p.get("trade_date")}
    out: list[dict[str, Any]] = []
    for p in ls_nav:
        d = p.get("trade_date")
        bv = bm_map.get(d)
        if d is None or bv is None or bv == 0:
            continue
        out.append({"trade_date": d, "value": float(p["value"]) / float(bv)})
    return out


class BacktestRunQueryService:
    def __init__(self) -> None:
        self._model = BacktestRunModel()

    def list_runs(self, limit: int = 50) -> list[dict]:
        return [_row_to_list_item(r) for r in self._model.list_recent(limit)]

    def get_run(self, run_id: str) -> dict | None:
        row = self._model.get_by_run_id(run_id)
        if row is None:
            return None
        item = _row_to_list_item(row)
        summary = row.summary_json if isinstance(row.summary_json, dict) else {}
        returns_rows: list[dict[str, Any]] = []
        ic_rows: list[dict[str, Any]] = []
        turnover_rows: list[dict[str, Any]] = []
        if row.output_dir:
            out = Path(row.output_dir)
            report_path = out / "report.json"
            if report_path.is_file():
                try:
                    summary = json.loads(report_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            returns_rows = _read_parquet_rows(out / "returns.parquet")
            ic_rows = _read_parquet_rows(out / "ic.parquet")
            turnover_rows = _read_parquet_rows(out / "turnover.parquet")

        item["summary"] = summary
        item["returns"] = returns_rows
        item["ic"] = ic_rows
        item["turnover_series"] = turnover_rows
        item["group_totals"] = _group_totals(returns_rows)
        item["yearly"] = _yearly_metrics(returns_rows, "long_short")
        item["warnings"] = list(summary.get("warnings") or [])
        item["cost"] = summary.get("cost") or {}
        item["benchmark"] = summary.get("benchmark") or BENCHMARK_CODE

        nav_curves: dict[str, list[dict[str, Any]]] = {
            "long_short": _cum_nav(returns_rows, "long_short"),
        }
        gcols = _group_cols(returns_rows)
        if gcols:
            nav_curves["top"] = _cum_nav(returns_rows, gcols[0])
            nav_curves["bottom"] = _cum_nav(returns_rows, gcols[-1])

        trade_dates = [
            str(r["trade_date"])
            for r in returns_rows
            if r.get("trade_date")
        ]
        start = row.start_date or (trade_dates[0] if trade_dates else "")
        end = row.end_date or (trade_dates[-1] if trade_dates else "")
        bm = _load_benchmark_nav(start, end, trade_dates) if start and end else []
        nav_curves["benchmark"] = bm
        nav_curves["excess"] = _align_excess(nav_curves["long_short"], bm)
        item["nav_curves"] = nav_curves
        return item

    def get_table(
        self,
        run_id: str,
        name: str,
        *,
        trade_date: str | None = None,
        group_id: str | None = None,
        ts_code: str | None = None,
        limit: int = 5000,
    ) -> dict | None:
        row = self._model.get_by_run_id(run_id)
        if row is None or not row.output_dir:
            return None
        name = (name or "").strip().lower()
        if name not in ("portfolio", "trades", "returns"):
            raise ValueError("name 仅支持 portfolio | trades | returns")
        path = Path(row.output_dir) / f"{name}.parquet"
        if not path.is_file():
            return None
        try:
            df = pl.read_parquet(path)
        except Exception:
            return None

        if trade_date and "trade_date" in df.columns:
            df = df.filter(pl.col("trade_date") == trade_date.strip())
        if group_id and "group_id" in df.columns:
            df = df.filter(pl.col("group_id") == group_id.strip())
        if ts_code and "ts_code" in df.columns:
            df = df.filter(pl.col("ts_code") == ts_code.strip())

        total = df.height
        limit = max(1, min(int(limit or 5000), 20000))
        if total > limit:
            df = df.head(limit)
        columns = list(df.columns)
        return {
            "name": name,
            "columns": columns,
            "rows": df.to_dicts() if not df.is_empty() else [],
            "total": total,
        }
