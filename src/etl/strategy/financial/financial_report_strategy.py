import time
from collections import defaultdict
from datetime import datetime
from queue import Queue

from src.common.function import format_micro_stock_postfix, scan_macro_snapshot_rows, tqdm_iter
from src.common.setting import settings
from src.etl.extract.local.financial.financial_report_local_extract import ReportExtract as LocalReportExtract
from src.etl.workflow.financial.financial_report_workflow import (
    ReportWorkflow,
    _REPORT_MISSING_ENTITIES,
    _REPORT_SPECS,
    _SPEC_BY_MISSING_ENTITY,
)
from src.service.stock.stock_base_service import StockBaseService


_REPORT_MACRO_DIMENSIONS: list[tuple[str, str]] = [
    ("report_income_count", "[宏观] 利润表检查"),
    ("report_balance_count", "[宏观] 资产负债表检查"),
    ("report_cashflow_count", "[宏观] 现金流量表检查"),
    ("report_indicator_count", "[宏观] 财务指标检查"),
]


_HISTORY_INIT_PROGRESS_PROTOCOL = """
若传入 progress_queue，帧顺序为：
算出期数后 put {"status": "running", "total"}；每期结束后 put
{"index", "total", "period", "saved"}；全部完成后 put
{"done": True, "periods": list[str]}。
（路由层会在任务开始时额外 put {"status": "started"}，便于客户端立刻收到首包。）
"""


class ReportStrategy:

    def __init__(self):
        self.report_workflow = ReportWorkflow()
        self.stock_base_service = StockBaseService()
        self.local_report_extract = LocalReportExtract()
        self.start_date_default = settings.etl_start_date("financial_report")

    # ------------------------------------------------------------------ #
    # 历史入库（按表）
    # ------------------------------------------------------------------ #

    def _run_history_init(
        self,
        report_type: str,
        start_date: str | None,
        progress_queue: Queue | None,
        *,
        finalize: bool,
    ) -> list[str]:
        """单表历史入库公共体；finalize=False 由编排层最后统一刷快照。"""
        spec = _REPORT_SPECS[report_type]
        start_date = start_date or self.start_date_default
        today = datetime.now().strftime("%Y%m%d")
        report_period = self.local_report_extract.list_periods_below_threshold(
            start_period_date=start_date,
            end_period_date=today,
            report_type=report_type,
        )
        total = len(report_period)
        if progress_queue is not None:
            progress_queue.put({"status": "running", "total": total})
        if finalize:
            self.refresh_report_macro_snapshot(label=spec.label, scan_dimensions=False)
        pbar = tqdm_iter(report_period, desc=f"历史{spec.label}{report_type}入库", unit="期")
        for index, period in enumerate(pbar, start=1):
            saved_count = self.report_workflow.report_by_period(report_type, period)
            pbar.set_postfix(saved=saved_count)
            if progress_queue is not None:
                progress_queue.put(
                    {
                        "index": index,
                        "total": total,
                        "period": period,
                        "saved": saved_count,
                    }
                )
        if progress_queue is not None:
            progress_queue.put({"done": True, "periods": list(report_period)})
        if finalize:
            self.refresh_report_macro_snapshot(label=spec.label, scan_dimensions=False)
        return report_period

    def report_income_history_init(
        self,
        start_date: str = None,
        *,
        progress_queue: Queue | None = None,
    ):
        """历史利润表全量入库。SSE 入口；CLI 批量入口见 report_history_init_all。"""
        return self._run_history_init("income", start_date, progress_queue, finalize=True)

    report_income_history_init.__doc__ += _HISTORY_INIT_PROGRESS_PROTOCOL

    def report_balance_history_init(
        self,
        start_date: str = None,
        *,
        progress_queue: Queue | None = None,
    ):
        """历史资产负债表全量入库。SSE 入口；CLI 批量入口见 report_history_init_all。"""
        return self._run_history_init("balance", start_date, progress_queue, finalize=True)

    report_balance_history_init.__doc__ += _HISTORY_INIT_PROGRESS_PROTOCOL

    def report_cashflow_history_init(
        self,
        start_date: str = None,
        *,
        progress_queue: Queue | None = None,
    ):
        """历史现金流量表全量入库。SSE 入口;CLI 批量入口见 report_history_init_all。"""
        return self._run_history_init("cashflow", start_date, progress_queue, finalize=True)

    report_cashflow_history_init.__doc__ += _HISTORY_INIT_PROGRESS_PROTOCOL

    def report_indicator_history_init(
        self,
        start_date: str = None,
        *,
        progress_queue: Queue | None = None,
    ):
        """历史财务指标全量入库。SSE 入口；CLI 批量入口见 report_history_init_all。"""
        return self._run_history_init("indicator", start_date, progress_queue, finalize=True)

    report_indicator_history_init.__doc__ += _HISTORY_INIT_PROGRESS_PROTOCOL

    def report_history_init_all(self, start_date: str | None = None) -> dict[str, list[str]]:
        """
        CLI 批量编排：income→balance→cashflow→indicator 四表顺序入库，跑完统一一次 Phase 4 刷快照
        （单表 SSE 路径仍走 report_*_history_init，各自 finalize）。
        """
        periods: dict[str, list[str]] = {}
        self.refresh_report_macro_snapshot(scan_dimensions=False)
        for report_type in ("income", "balance", "cashflow", "indicator"):
            periods[report_type] = self._run_history_init(
                report_type, start_date, progress_queue=None, finalize=False
            )
        self.refresh_report_macro_snapshot(scan_dimensions=False)
        return periods

    # ------------------------------------------------------------------ #
    # 微观完整性检查
    # ------------------------------------------------------------------ #

    def check_report_complete_history(self, missing_entity: str) -> int:
        """
        全 A 股逐只检查指定财报表在区间内的季度报告期是否齐全，缺期则写 log 并 Tushare 补拉。

        区间: [max("20050101", list_date), 今日]；list_date 来自 stock_list（须先 pull-list-a）。

        Returns:
            本轮发现的缺期条目总数（格式 ts_code,end_date 的条数，非去重股票数）。
        """
        if missing_entity not in _REPORT_MISSING_ENTITIES:
            raise ValueError(
                f"missing_entity 须为 {_REPORT_MISSING_ENTITIES} 之一，收到: {missing_entity!r}"
            )
        spec = _SPEC_BY_MISSING_ENTITY[missing_entity]
        label = spec.label
        print(f"[微观] 开始检查{label}完整性（逐股查漏补拉）...")

        # 一次性预加载该表所有 (ts_code, end_date)，消除逐股 SELECT 的 N+1
        t0 = time.monotonic()
        all_rows = spec.query_all(self.report_workflow, ("ts_code", "end_date"))
        stock_to_periods: dict[str, list[str]] = defaultdict(list)
        for row in all_rows:
            stock_cell, end_cell = row[0], row[1]
            if not stock_cell or not end_cell:
                continue
            stock_to_periods[str(stock_cell).strip()].append(str(end_cell).strip())
        for code in stock_to_periods:
            stock_to_periods[code].sort()
        print(
            f"[微观] {label}预加载完成：{len(stock_to_periods)} 股，"
            f"耗时 {time.monotonic() - t0:.1f}s"
        )

        stock_list = self.stock_base_service.get_all_stock_list_a()
        stock_list = [
            s for s in stock_list
            if not getattr(s, "delist_date", None)
        ]
        missing_all: list[str] = []
        passed_stocks = 0
        failed_stocks = 0
        active_stocks = len(stock_list)
        vip_pulled_periods: set[str] = set()
        pbar = tqdm_iter(stock_list, desc=f"[微观] 检查{label}完整性", unit="股票")
        end_today = datetime.now().strftime("%Y%m%d")
        for inst in pbar:
            ts_code = getattr(inst, "ts_code", None)
            if not ts_code:
                pbar.set_postfix(
                    **format_micro_stock_postfix(
                        active_stocks=active_stocks,
                        passed_stocks=passed_stocks,
                        failed_stocks=failed_stocks,
                        missing_items=len(missing_all),
                        missing_key="缺期",
                    )
                )
                continue
            list_date = getattr(inst, "list_date", None)
            start_date = max("19900101", list_date or "19900101")

            missing_periods = self.report_workflow.check_report_complete_by_ts_code(
                ts_code=ts_code,
                missing_entity=missing_entity,
                start_end_date=start_date,
                end_end_date=end_today,
                end_dates=stock_to_periods.get(str(ts_code).strip(), []),
                vip_pulled_periods=vip_pulled_periods,
            )
            if missing_periods:
                failed_stocks += 1
            else:
                passed_stocks += 1
            missing_all.extend(f"{ts_code},{ed}" for ed in missing_periods)
            pbar.set_postfix(
                **format_micro_stock_postfix(
                    active_stocks=active_stocks,
                    passed_stocks=passed_stocks,
                    failed_stocks=failed_stocks,
                    missing_items=len(missing_all),
                    missing_key="缺期",
                )
            )
        n = len(missing_all)
        print(
            f"[微观] {label}检查完成：活跃{active_stocks}股 "
            f"通过{passed_stocks}股 缺失{failed_stocks}股 缺期{n}条"
        )
        return n

    def check_report_complete_history_all_with_snapshot(self) -> int:
        """三表微观完整性检查，前后刷新宏观快照。"""
        self.refresh_report_macro_snapshot(scan_dimensions=True)
        total = 0
        for entity in ("financial_report_income", "financial_report_balance", "financial_report_cashflow", "financial_report_indicator"):
            total += self.check_report_complete_history(entity)
        self.refresh_report_macro_snapshot(scan_dimensions=False)
        print(f"[微观] 财报全维度检查完成，累计缺期 {total} 条")
        return total

    # ------------------------------------------------------------------ #
    # 宏观快照
    # ------------------------------------------------------------------ #

    def refresh_report_macro_snapshot(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        *,
        label: str = "财报",
        scan_dimensions: bool = True,
    ) -> int:
        """刷新 report_period_count 宏观快照：可选三表 tqdm + 落库。"""
        if start_date is None:
            start_date = self.start_date_default
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")
        start = (start_date or "").strip()
        end = (end_date or "").strip()
        if not start or not end or start > end:
            return 0
        print(f"[宏观] 刷新{label}完整性快照 {start}~{end} ...")
        t0 = time.monotonic()
        merged = self.report_workflow.build_report_period_count_rows(
            start_date=start,
            end_date=end,
        )
        if not merged:
            print("[宏观] 无报告期数据，跳过")
            return 0
        if scan_dimensions:
            for count_field, desc in _REPORT_MACRO_DIMENSIONS:
                stats = scan_macro_snapshot_rows(
                    merged,
                    count_field=count_field,
                    desc=desc,
                    unit="期",
                )
                print(
                    f"[宏观] {desc}完成：活跃{stats['active_stock']}股 "
                    f"通过{stats['pass_days']}期 缺失{stats['fail_days']}期 "
                    f"缺条{stats['missing_records']}"
                )
        n = self.report_workflow.load_report_period_count_rows(merged)
        elapsed = time.monotonic() - t0
        suffix = "" if scan_dimensions else "（无维度扫描）"
        print(f"[宏观] 快照落库 {n} 条{suffix}，耗时 {elapsed:.1f}s")
        return n
