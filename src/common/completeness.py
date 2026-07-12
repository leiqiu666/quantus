"""通用完整性保障引擎：宏观快照 + 微观补拉。

支持四类数据源：
- by-date 全市场（daily_basic, moneyflow 等）：按交易日统计、全市场补拉
- by-period 全市场（forecast, express）：按报告期统计、全市场补拉
- by-ts_code 逐股（stk_holdernumber 补位等）：按报告期/逐股扫缺口补拉
- by-index 逐指数（index_weight / index_daily）：按月或按交易日统计、逐指数扫缺口补拉
"""

from __future__ import annotations

import queue
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Literal

from sqlalchemy import func

from src.common.database import Database
from src.common.function import (
    MACRO_COMPLETE_THRESHOLD,
    report_period_generate,
    tqdm_iter,
)
from src.entities.data_entities.completeness_snapshot_entities import (
    CompletenessSnapshotEntities,
)
from src.service.stock.stock_active_count_service import StockActiveCountService
from src.service.stock.stock_base_service import StockBaseService
from src.etl.transform.stock.stock_transform import StockTransform


def _norm_date(v: Any) -> str | None:
    if v is None:
        return None
    s = str(v).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else None


@dataclass
class CompletenessConfig:
    source_name: str
    entity_class: Any
    date_column: str
    start_date: str
    is_period: bool = False
    annual_only: bool = False
    event_driven: bool = False
    threshold: float = MACRO_COMPLETE_THRESHOLD
    period_stock_count_fn: Callable[[list[Any], str], int] | None = None
    pull_by_date: Callable[[str], int] | None = None
    pull_by_stock: Callable[..., int] | None = None
    pull_by_index: Callable[..., int] | None = None
    index_codes: tuple[str, ...] | None = None
    index_column: str = "index_code"
    index_date_unit: Literal["month", "day"] = "month"


class CompletenessEngine:
    """通用完整性保障引擎。"""

    def __init__(self, config: CompletenessConfig) -> None:
        self.config = config
        self.db = Database()
        self.stock_service = StockBaseService()
        self.active_count_service = StockActiveCountService()
        self._stock_transform = StockTransform()

    # ── 宏观快照 ──────────────────────────────────────────────

    def refresh_snapshot(
        self, start: str | None = None, end: str | None = None
    ) -> int:
        start = (start or self.config.start_date).strip()
        end = (end or datetime.now().strftime("%Y%m%d")).strip()
        if not start or start > end:
            return 0

        stock_rows = self.stock_service.get_all_stock_list_a()

        if self.config.is_period:
            periods = report_period_generate(start, end)
            if self.config.annual_only:
                periods = [p for p in periods if p.endswith("1231")]
            expected = self.active_count_service.resolve_listed_counts(periods)
            if any(expected.get(p, 0) <= 0 for p in periods):
                computed = self._stock_transform.period_stock_count(
                    stock_rows, start, end,
                )
                for p in periods:
                    if expected.get(p, 0) <= 0:
                        expected[p] = computed.get(p, 0)
        else:
            from src.etl.extract.local.stock.stock_trade_calendar_local_extract import (
                TradeCalLocalExtract,
            )
            from src.etl.strategy.stock.stock_trade_calendar_strategy import (
                TradeCalStrategy,
            )

            TradeCalStrategy().ensure_trade_cal(start_date=start, end_date=end)
            open_dates = TradeCalLocalExtract().get_open_trade_dates(
                start_date=start, end_date=end
            )
            if (
                self.config.index_codes
                and self.config.index_date_unit == "day"
            ):
                expected = {
                    td: len(self.config.index_codes) for td in open_dates
                }
            elif self.config.event_driven:
                expected = {td: 1 for td in open_dates}
            elif self.config.period_stock_count_fn is not None:
                fn = self.config.period_stock_count_fn
                expected = {td: fn(stock_rows, td) for td in open_dates}
            else:
                expected = self.active_count_service.resolve_trading_counts(open_dates)
                for td in open_dates:
                    if td not in expected or expected[td] <= 0:
                        expected[td] = self._trade_date_stock_count(
                            stock_rows, [td],
                        ).get(td, 0)

        actual = self._count_rows_by_date(start, end)
        prev_snapshot = (
            self._load_snapshot_map(start, end) if self.config.event_driven else {}
        )

        records = []
        for dk, sc in expected.items():
            resolved = actual.get(dk, 0)
            if self.config.event_driven:
                prev_res = prev_snapshot.get(dk, (1, 0))[1]
                if resolved >= 1:
                    resolved = max(resolved, 1)
                elif prev_res >= 1:
                    resolved = 1
                else:
                    resolved = 0
            records.append(
                {
                    "source_name": self.config.source_name,
                    "date_key": dk,
                    "period_stock_count": sc,
                    "resolved_count": resolved,
                }
            )
        if not records:
            return 0

        return self._upsert_snapshot(records)

    def scan_below_threshold(
        self,
        threshold: float | None = None,
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> list[str]:
        if threshold is None:
            threshold = self.config.threshold
        session = self.db.get_session()
        try:
            q = session.query(CompletenessSnapshotEntities).filter_by(
                source_name=self.config.source_name
            )
            if start:
                q = q.filter(CompletenessSnapshotEntities.date_key >= start)
            if end:
                q = q.filter(CompletenessSnapshotEntities.date_key <= end)
            rows = q.all()
            below = []
            for r in rows:
                if r.period_stock_count and r.period_stock_count > 0:
                    if r.resolved_count / r.period_stock_count < threshold:
                        below.append(r.date_key)
            return sorted(below)
        finally:
            session.close()

    def backfill_keys(
        self,
        start: str | None = None,
        end: str | None = None,
        *,
        threshold: float | None = None,
    ) -> list[str]:
        """刷新快照并返回区间内未达阈值的 date_key / period（升序）。"""
        if threshold is None:
            threshold = self.config.threshold
        start = (start or self.config.start_date).strip()
        end = (end or datetime.now().strftime("%Y%m%d")).strip()
        if not start or start > end:
            return []
        self.refresh_snapshot(start, end)
        return self.scan_below_threshold(threshold, start=start, end=end)

    def mark_date_pulled(self, date_key: str) -> None:
        """事件型数据源：标记某日已拉取（含 0 条），避免重复空拉。"""
        dk = (date_key or "").strip()
        if not dk:
            return
        self._upsert_snapshot(
            [
                {
                    "source_name": self.config.source_name,
                    "date_key": dk,
                    "period_stock_count": 1,
                    "resolved_count": 1,
                }
            ]
        )

    def print_scan(self, *, start: str | None = None, end: str | None = None) -> int:
        below = self.scan_below_threshold(start=start, end=end)
        src = self.config.source_name
        if below:
            print(f"[{src}] {len(below)} 个缺口: {below[:5]}{'...' if len(below) > 5 else ''}")
        else:
            print(f"[{src}] 全部达标")
        return len(below)

    # ── 全市场补拉 ────────────────────────────────────────────

    def backfill_missing(
        self,
        missing: list[str] | None = None,
        *,
        progress_queue: queue.Queue | None = None,
    ) -> int:
        if missing is None:
            missing = self.scan_below_threshold()
        if not missing:
            return 0
        assert self.config.pull_by_date is not None
        unit = "期" if self.config.is_period else "日"
        total_steps = len(missing)
        if progress_queue is not None:
            progress_queue.put({"status": "running", "total": total_steps})

        def _pull_one(dk: str) -> int:
            try:
                n = self.config.pull_by_date(dk)
            except Exception as exc:
                print(f"[{self.config.source_name}] 补拉 {dk} 失败: {exc}")
                return 0
            if isinstance(n, tuple):
                return sum(n)
            return n

        total = 0
        if progress_queue is not None:
            for i, dk in enumerate(missing, 1):
                saved = _pull_one(dk)
                total += saved
                progress_queue.put({
                    "index": i,
                    "total": total_steps,
                    "period": dk,
                    "saved": saved,
                })
        else:
            for dk in tqdm_iter(
                missing, desc=f"[{self.config.source_name}] 补拉", unit=unit,
            ):
                total += _pull_one(dk)
        return total

    # ── 完整流程（全市场） ────────────────────────────────────

    def check_complete(
        self,
        start: str | None = None,
        end: str | None = None,
        *,
        progress_queue: queue.Queue | None = None,
    ) -> int:
        start = (start or self.config.start_date).strip()
        end = (end or datetime.now().strftime("%Y%m%d")).strip()
        if not start or start > end:
            return 0

        if progress_queue is not None:
            progress_queue.put({"log": f"刷新快照 {start}~{end}"})
        print(f"[{self.config.source_name}] 刷新快照 {start}~{end}")
        self.refresh_snapshot(start, end)
        self.print_scan(start=start, end=end)

        missing = self.scan_below_threshold(start=start, end=end)
        if not missing:
            if progress_queue is not None:
                progress_queue.put({"log": "全部达标，无需补拉"})
            return 0
        print(f"[{self.config.source_name}] {len(missing)} 个缺口，开始补拉")
        if progress_queue is not None:
            progress_queue.put({"log": f"{len(missing)} 个缺口，开始补拉"})
        total = self.backfill_missing(missing, progress_queue=progress_queue)
        if total:
            self.refresh_snapshot(start, end)
            self.print_scan(start=start, end=end)
        return total

    # ── 逐股补拉 ─────────────────────────────────────────────

    def check_complete_per_stock(
        self,
        start: str | None = None,
        end: str | None = None,
        *,
        progress_queue: queue.Queue | None = None,
    ) -> int:
        assert self.config.pull_by_stock is not None
        start = (start or self.config.start_date).strip()
        end = (end or datetime.now().strftime("%Y%m%d")).strip()
        if not start or start > end:
            return 0

        if progress_queue is not None:
            progress_queue.put({"log": f"刷新快照 {start}~{end}"})
        print(f"[{self.config.source_name}] 刷新快照 {start}~{end}")
        self.refresh_snapshot(start, end)
        self.print_scan(start=start, end=end)

        stock_rows = self.stock_service.get_all_stock_list_a()
        existing = self._load_existing_by_stock()
        total = 0
        total_steps = len(stock_rows)
        if progress_queue is not None:
            progress_queue.put({"status": "running", "total": total_steps})

        if self.config.is_period:
            all_periods = report_period_generate(start, end)
            if self.config.annual_only:
                all_periods = [p for p in all_periods if p.endswith("1231")]
        else:
            from src.etl.extract.local.stock.stock_trade_calendar_local_extract import (
                TradeCalLocalExtract,
            )
            from src.etl.strategy.stock.stock_trade_calendar_strategy import (
                TradeCalStrategy,
            )

            TradeCalStrategy().ensure_trade_cal(start, end)
            all_periods = TradeCalLocalExtract().get_open_trade_dates(start, end)

        pbar = None if progress_queue is not None else tqdm_iter(
            stock_rows,
            desc=f"[{self.config.source_name}] 逐股检查",
            unit="股",
        )
        row_iter = stock_rows if progress_queue is not None else pbar
        for i, row in enumerate(row_iter, 1):
            ts_code = getattr(row, "ts_code", None)
            if not ts_code:
                continue
            ts_code = str(ts_code).strip()

            ld = _norm_date(getattr(row, "list_date", None))
            dd = _norm_date(getattr(row, "delist_date", None))
            if not ld:
                continue

            eff_start = max(ld, start)
            eff_end = min(dd, end) if dd else end
            if eff_start > eff_end:
                continue

            expected = [p for p in all_periods if eff_start <= p <= eff_end]
            resolved = set(existing.get(ts_code, []))
            missing = [p for p in expected if p not in resolved]
            if not missing:
                continue

            n = self.config.pull_by_stock(
                ts_code=ts_code, start_date=missing[0], end_date=missing[-1]
            )
            total += n
            if progress_queue is not None:
                progress_queue.put({
                    "index": i,
                    "total": total_steps,
                    "period": ts_code,
                    "saved": n,
                })
            elif pbar is not None:
                pbar.set_postfix(补=total, 缺口=len(missing))
        return total

    # ── 逐指数补拉 ───────────────────────────────────────────

    INDEX_CODES = [
        "000300.SH",
        "000905.SH",
        "000852.SH",
        "399006.SZ",
    ]

    def check_complete_per_index(
        self,
        start: str | None = None,
        end: str | None = None,
        *,
        progress_queue: queue.Queue | None = None,
    ) -> int:
        assert self.config.pull_by_index is not None
        start = (start or self.config.start_date).strip()
        end = (end or datetime.now().strftime("%Y%m%d")).strip()
        if not start or start > end:
            return 0

        if progress_queue is not None:
            progress_queue.put({"log": f"刷新快照 {start}~{end}"})
        print(f"[{self.config.source_name}] 刷新快照 {start}~{end}")
        self.refresh_snapshot(start, end)
        self.print_scan(start=start, end=end)

        index_codes = self.config.index_codes or tuple(self.INDEX_CODES)
        existing = self._load_existing_by_index()
        if self.config.index_date_unit == "day":
            from src.etl.extract.local.stock.stock_trade_calendar_local_extract import (
                TradeCalLocalExtract,
            )
            from src.etl.strategy.stock.stock_trade_calendar_strategy import (
                TradeCalStrategy,
            )

            TradeCalStrategy().ensure_trade_cal(start, end)
            date_keys = TradeCalLocalExtract().get_open_trade_dates(
                start_date=start, end_date=end,
            )
            flat_tasks: list[tuple[str, str, str]] = []
            for idx_code in index_codes:
                resolved = set(existing.get(idx_code, []))
                missing = [td for td in date_keys if td not in resolved]
                if not missing:
                    continue
                flat_tasks.append((idx_code, missing[0], missing[-1]))
        else:
            months = self._generate_months(start, end)
            flat_tasks = []
            for idx_code in index_codes:
                resolved = set(existing.get(idx_code, []))
                missing = [m for m in months if m not in resolved]
                for m in missing:
                    flat_tasks.append((idx_code, f"{m}01", self._month_end(m)))

        total = 0
        if progress_queue is not None:
            progress_queue.put({"status": "running", "total": len(flat_tasks) or 1})
            for step, task in enumerate(flat_tasks, 1):
                idx_code, task_start, task_end = task
                n = self.config.pull_by_index(
                    index_code=idx_code,
                    start_date=task_start,
                    end_date=task_end,
                )
                total += n
                period = (
                    f"{idx_code}/{task_start}"
                    if self.config.index_date_unit == "day"
                    else f"{idx_code}/{task_start[:6]}"
                )
                progress_queue.put({
                    "index": step,
                    "total": len(flat_tasks),
                    "period": period,
                    "saved": n,
                })
            return total

        for idx_code in tqdm_iter(
            index_codes,
            desc=f"[{self.config.source_name}] 逐指数检查",
            unit="指数",
        ):
            resolved = set(existing.get(idx_code, []))
            if self.config.index_date_unit == "day":
                from src.etl.extract.local.stock.stock_trade_calendar_local_extract import (
                    TradeCalLocalExtract,
                )
                from src.etl.strategy.stock.stock_trade_calendar_strategy import (
                    TradeCalStrategy,
                )

                TradeCalStrategy().ensure_trade_cal(start, end)
                date_keys = TradeCalLocalExtract().get_open_trade_dates(
                    start_date=start, end_date=end,
                )
                missing = [td for td in date_keys if td not in resolved]
                if not missing:
                    continue
                n = self.config.pull_by_index(
                    index_code=idx_code,
                    start_date=missing[0],
                    end_date=missing[-1],
                )
                total += n
                continue

            months = self._generate_months(start, end)
            missing = [m for m in months if m not in resolved]
            if not missing:
                continue
            for m in missing:
                n = self.config.pull_by_index(
                    index_code=idx_code,
                    start_date=f"{m}01",
                    end_date=self._month_end(m),
                )
                total += n
        return total

    # ── 内部方法 ──────────────────────────────────────────────

    def _period_stock_count(
        self, stock_rows: list[Any], periods: list[str]
    ) -> dict[str, int]:
        counts = {p: 0 for p in periods}
        for row in stock_rows:
            ld = _norm_date(getattr(row, "list_date", None))
            dd = _norm_date(getattr(row, "delist_date", None))
            if not ld:
                continue
            for p in periods:
                if ld <= p and (dd is None or dd > p):
                    counts[p] += 1
        return counts

    def _trade_date_stock_count(
        self, stock_rows: list[Any], trade_dates: list[str]
    ) -> dict[str, int]:
        counts = {td: 0 for td in trade_dates}
        for row in stock_rows:
            ld = _norm_date(getattr(row, "list_date", None))
            dd = _norm_date(getattr(row, "delist_date", None))
            if not ld:
                continue
            for td in trade_dates:
                if ld <= td and (dd is None or dd > td):
                    counts[td] += 1
        return counts

    def _load_snapshot_map(
        self, start: str, end: str
    ) -> dict[str, tuple[int, int]]:
        session = self.db.get_session()
        try:
            rows = (
                session.query(CompletenessSnapshotEntities)
                .filter_by(source_name=self.config.source_name)
                .filter(
                    CompletenessSnapshotEntities.date_key >= start,
                    CompletenessSnapshotEntities.date_key <= end,
                )
                .all()
            )
            return {
                r.date_key: (r.period_stock_count or 0, r.resolved_count or 0)
                for r in rows
            }
        finally:
            session.close()

    def _count_rows_by_date(self, start: str, end: str) -> dict[str, int]:
        session = self.db.get_session()
        try:
            col = getattr(self.config.entity_class, self.config.date_column)
            rows = (
                session.query(col, func.count())
                .filter(col >= start, col <= end)
                .group_by(col)
                .all()
            )
            return {str(r[0]).replace("-", "")[:8]: r[1] for r in rows}
        finally:
            session.close()

    def _upsert_snapshot(self, records: list[dict]) -> int:
        session = self.db.get_session()
        try:
            for rec in records:
                existing = (
                    session.query(CompletenessSnapshotEntities)
                    .filter_by(
                        source_name=rec["source_name"],
                        date_key=rec["date_key"],
                    )
                    .first()
                )
                if existing:
                    existing.period_stock_count = rec["period_stock_count"]
                    existing.resolved_count = rec["resolved_count"]
                else:
                    session.add(CompletenessSnapshotEntities(**rec))
            session.commit()
            return len(records)
        finally:
            session.close()

    def _load_existing_by_stock(self) -> dict[str, list[str]]:
        session = self.db.get_session()
        try:
            ts_col = getattr(self.config.entity_class, "ts_code", None)
            dt_col = getattr(self.config.entity_class, self.config.date_column)
            if ts_col is None:
                return {}
            rows = session.query(ts_col, dt_col).all()
            result: dict[str, list[str]] = {}
            for r in rows:
                tc = str(r[0]).strip()
                dk = str(r[1]).replace("-", "")[:8]
                result.setdefault(tc, []).append(dk)
            return result
        finally:
            session.close()

    def _load_existing_by_index(self) -> dict[str, list[str]]:
        session = self.db.get_session()
        try:
            idx_col = getattr(self.config.entity_class, self.config.index_column, None)
            dt_col = getattr(self.config.entity_class, self.config.date_column)
            if idx_col is None:
                return {}
            rows = session.query(idx_col, dt_col).all()
            key_len = 8 if self.config.index_date_unit == "day" else 6
            result: dict[str, list[str]] = {}
            for r in rows:
                ic = str(r[0]).strip()
                dk = str(r[1]).replace("-", "")[:key_len]
                result.setdefault(ic, []).append(dk)
            return result
        finally:
            session.close()

    @staticmethod
    def _month_end(ym: str) -> str:
        if ym[4:] in ("01", "03", "05", "07", "08", "10", "12"):
            return f"{ym[:4]}{ym[4:]}31"
        if ym[4:] in ("04", "06", "09", "11"):
            return f"{ym[:4]}{ym[4:]}30"
        return f"{ym[:4]}{ym[4:]}28"

    @staticmethod
    def _generate_months(start: str, end: str) -> list[str]:
        sy, sm = int(start[:4]), int(start[4:6])
        ey, em = int(end[:4]), int(end[4:6])
        months = []
        y, m = sy, sm
        while (y, m) <= (ey, em):
            months.append(f"{y:04d}{m:02d}")
            m += 1
            if m > 12:
                m = 1
                y += 1
        return months
