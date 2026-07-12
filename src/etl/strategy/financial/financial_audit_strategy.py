"""财务审计意见 Strategy：按报告期 × 缺口股拉取（仅年报）。"""

from __future__ import annotations

from datetime import datetime

from src.common.function import report_period_generate, tqdm_iter
from src.common.setting import settings
from src.etl.extract.local.financial.financial_audit_local_extract import AuditLocalExtract
from src.etl.workflow.financial.financial_audit_workflow import AuditWorkflow
from src.common.completeness import CompletenessConfig, CompletenessEngine
from src.entities.data_entities.financial.financial_audit_entities import FinaAuditEntities
from src.service.stock.stock_base_service import StockBaseService


class AuditStrategy:
    def __init__(self) -> None:
        self.audit_workflow = AuditWorkflow()
        self.audit_local = AuditLocalExtract()
        self.stock_base_service = StockBaseService()
        self.audit_start_date = settings.etl_start_date("financial_audit")

    def _active_ts_codes(self, period: str) -> list[str]:
        stock_rows = self.stock_base_service.get_all_stock_list_a()
        codes: list[str] = []
        for row in stock_rows:
            ts_code = str(getattr(row, "ts_code", "") or "").strip()
            if not ts_code:
                continue
            list_date = str(getattr(row, "list_date", "") or "").strip()
            delist_date = str(getattr(row, "delist_date", "") or "").strip()
            if list_date and list_date > period:
                continue
            if delist_date and delist_date <= period:
                continue
            codes.append(ts_code)
        return codes

    def pull_fina_audit_gaps_for_period(self, period: str) -> int:
        """仅补拉该报告期库内缺失的 ts_code。"""
        period = (period or "").strip()
        if not period:
            return 0

        existing = self.audit_local.load_ts_codes_by_periods([period]).get(period, set())
        pending = [c for c in self._active_ts_codes(period) if c not in existing]
        if not pending:
            return 0

        total_saved = 0
        pbar = tqdm_iter(pending, desc=f"审计意见补拉 {period}", unit="股")
        for ts_code in pbar:
            n = self.audit_workflow.pull_fina_audit_by_period(
                ts_code=ts_code, period=period,
            )
            total_saved += n
            pbar.set_postfix(saved=n, total=total_saved)
        return total_saved

    def pull_fina_audit_by_period(
        self,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> int:
        if start_period is None:
            start_period = self.audit_start_date
        if end_period is None:
            end_period = f"{datetime.now().year - 1}1231"

        floor = (start_period or "").strip()
        end = (end_period or "").strip()
        if not floor or not end or floor > end:
            return 0

        eff_start = self.audit_local.resolve_incremental_start(configured_start=floor)
        if not eff_start or eff_start > end:
            max_end = self.audit_local.get_max_end_date()
            print(f"[信息] fina_audit 已同步至 {max_end or '无'}，跳过")
            return 0

        all_periods = report_period_generate(eff_start, end)
        periods = [p for p in all_periods if p.endswith("1231")]
        if not periods:
            print(f"[信息] {eff_start}~{end} 无年报期")
            return 0

        existing_by_period = self.audit_local.load_ts_codes_by_periods(periods)
        total_pending = 0
        for period in periods:
            existing = existing_by_period.get(period, set())
            total_pending += sum(
                1 for c in self._active_ts_codes(period) if c not in existing
            )

        print(
            f"[信息] {eff_start}~{end} 共 {len(periods)} 个年报期，"
            f"待补 {total_pending} 条（跳过库内已有）"
        )

        self.refresh_completeness_snapshot(start_date=floor, end_date=end)

        total_saved = 0
        for period in periods:
            n = self.pull_fina_audit_gaps_for_period(period)
            total_saved += n

        self.refresh_completeness_snapshot(start_date=floor, end_date=end)
        return total_saved

    @property
    def _completeness(self) -> CompletenessEngine:
        return CompletenessEngine(CompletenessConfig(
            source_name="financial_audit",
            entity_class=FinaAuditEntities,
            date_column="end_date",
            start_date=self.audit_start_date,
            is_period=True,
            annual_only=True,
            pull_by_date=lambda period: self.pull_fina_audit_gaps_for_period(period),
        ))

    def refresh_completeness_snapshot(self, start_date=None, end_date=None) -> int:
        return self._completeness.refresh_snapshot(start_date, end_date)

    def check_complete(self, start_date=None, end_date=None, *, progress_queue=None) -> int:
        return self._completeness.check_complete(start_date, end_date, progress_queue=progress_queue)
