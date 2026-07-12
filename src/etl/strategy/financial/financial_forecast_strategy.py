"""业绩预告 Strategy：按报告期全市场拉取、95% 完整性守门。"""

from __future__ import annotations

from datetime import datetime

from src.common.function import tqdm_iter
from src.common.setting import settings
from src.etl.workflow.financial.financial_forecast_workflow import ForecastWorkflow
from src.common.completeness import CompletenessConfig, CompletenessEngine
from src.entities.data_entities.financial.financial_forecast_entities import ForecastEntities


class ForecastStrategy:
    def __init__(self) -> None:
        self.forecast_workflow = ForecastWorkflow()
        self.forecast_start_date = settings.etl_start_date("financial_forecast")

    def pull_forecast_vip_by_period(
        self,
        start_period: str | None = None,
        end_period: str | None = None,
    ) -> int:
        if start_period is None:
            start_period = self.forecast_start_date
        if end_period is None:
            now = datetime.now()
            y = now.year
            m = now.month
            if m <= 3:
                end_period = f"{y - 1}0930"
            elif m <= 6:
                end_period = f"{y - 1}1231"
            elif m <= 9:
                end_period = f"{y}0331"
            else:
                end_period = f"{y}0630"

        floor = (start_period or "").strip()
        end = (end_period or "").strip()
        if not floor or not end or floor > end:
            return 0

        pending = self._completeness.backfill_keys(floor, end)
        if not pending:
            print(f"[信息] {floor}~{end} forecast 已完整（≥95%），跳过")
            return 0

        print(
            f"[信息] {floor}~{end} 共 {len(pending)} 个报告期待补"
            f"（首期 {pending[0]}，末期 {pending[-1]}）"
        )

        total_saved = 0
        for period in tqdm_iter(pending, desc="业绩预告入库", unit="期"):
            n = self.forecast_workflow.pull_forecast_by_period(period=period)
            total_saved += n

        self.refresh_completeness_snapshot(start_date=floor, end_date=end)
        return total_saved

    @property
    def _completeness(self) -> CompletenessEngine:
        return CompletenessEngine(CompletenessConfig(
            source_name="financial_forecast",
            entity_class=ForecastEntities,
            date_column="end_date",
            start_date=self.forecast_start_date,
            is_period=True,
            pull_by_date=lambda p: self.forecast_workflow.pull_forecast_by_period(period=p),
        ))

    def refresh_completeness_snapshot(self, start_date=None, end_date=None) -> int:
        return self._completeness.refresh_snapshot(start_date, end_date)

    def check_complete(self, start_date=None, end_date=None, *, progress_queue=None) -> int:
        return self._completeness.check_complete(start_date, end_date, progress_queue=progress_queue)
