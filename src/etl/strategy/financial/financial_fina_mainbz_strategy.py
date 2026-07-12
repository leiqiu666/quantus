"""主营业务构成 Strategy：按报告期全市场 VIP 拉取。"""

from __future__ import annotations

from datetime import datetime

from src.common.completeness import CompletenessConfig, CompletenessEngine
from src.common.function import tqdm_iter
from src.common.setting import settings
from src.entities.data_entities.financial.financial_fina_mainbz_entities import FinaMainbzEntities
from src.etl.workflow.financial.financial_fina_mainbz_workflow import FinaMainbzWorkflow


def _default_end_period() -> str:
    now = datetime.now()
    y = now.year
    m = now.month
    if m <= 3:
        return f"{y - 1}0930"
    if m <= 6:
        return f"{y - 1}1231"
    if m <= 9:
        return f"{y}0331"
    return f"{y}0630"


class FinaMainbzStrategy:
    def __init__(self) -> None:
        self.workflow = FinaMainbzWorkflow()
        self.start_date = settings.etl_start_date("financial_fina_mainbz")

    def pull_fina_mainbz_by_period(
        self,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> int:
        if start_period is None:
            start_period = self.start_date
        if end_period is None:
            end_period = _default_end_period()

        floor = (start_period or "").strip()
        end = (end_period or "").strip()
        if not floor or not end or floor > end:
            return 0

        pending = self._completeness.backfill_keys(floor, end)
        if not pending:
            print(f"[信息] {floor}~{end} fina_mainbz 已完整（≥95%），跳过")
            return 0

        print(
            f"[信息] {floor}~{end} 共 {len(pending)} 个报告期待补"
            f"（首期 {pending[0]}，末期 {pending[-1]}）"
        )

        total_saved = 0
        for period in tqdm_iter(pending, desc="主营业务构成入库", unit="期"):
            n = self.workflow.pull_fina_mainbz_period(period=period)
            total_saved += n

        self.refresh_completeness_snapshot(start_date=floor, end_date=end)
        return total_saved

    @property
    def _completeness(self) -> CompletenessEngine:
        return CompletenessEngine(CompletenessConfig(
            source_name="financial_fina_mainbz",
            entity_class=FinaMainbzEntities,
            date_column="end_date",
            start_date=self.start_date,
            is_period=True,
            pull_by_date=lambda period: self.workflow.pull_fina_mainbz_period(
                period=period,
            ),
        ))

    def refresh_completeness_snapshot(self, start_date=None, end_date=None) -> int:
        return self._completeness.refresh_snapshot(start_date, end_date)

    def check_complete(self, start_date=None, end_date=None, *, progress_queue=None) -> int:
        return self._completeness.check_complete(start_date, end_date, progress_queue=progress_queue)
