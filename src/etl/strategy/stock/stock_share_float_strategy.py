"""限售股解禁 Strategy：按解禁日编排、event_driven 完整性守门。"""

from __future__ import annotations

from datetime import datetime

from src.common.completeness import CompletenessConfig, CompletenessEngine
from src.common.function import tqdm_iter
from src.common.setting import settings
from src.entities.data_entities.stock.stock_share_float_entities import StockShareFloatEntities
from src.etl.strategy.stock.stock_trade_calendar_strategy import TradeCalStrategy
from src.etl.workflow.stock.stock_share_float_workflow import StockShareFloatWorkflow


class StockShareFloatStrategy:
    def __init__(self) -> None:
        self.share_float_workflow = StockShareFloatWorkflow()
        self.trade_cal_strategy = TradeCalStrategy()
        self.share_float_start_date = settings.etl_start_date("stock_share_float")

    def pull_share_float_by_date(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        if start_date is None:
            start_date = self.share_float_start_date
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        floor = (start_date or "").strip()
        end = (end_date or "").strip()
        if not floor or not end or floor > end:
            return 0

        self.trade_cal_strategy.ensure_trade_cal(
            start_date=floor,
            end_date=end,
            exchange="SSE",
        )

        pending = self._completeness.backfill_keys(floor, end)
        if not pending:
            print(f"[信息] {floor}~{end} stock_share_float 已完整，跳过")
            return 0

        print(
            f"[信息] {floor}~{end} 共 {len(pending)} 个解禁日待补"
            f"（首日 {pending[0]}，末日 {pending[-1]}）"
        )

        total_saved = 0
        for float_date in tqdm_iter(pending, desc="限售股解禁入库", unit="日"):
            n = self.share_float_workflow.pull_share_float_by_float_date(float_date=float_date)
            total_saved += n
            if n == 0:
                self._completeness.mark_date_pulled(float_date)

        self.refresh_completeness_snapshot(start_date=floor, end_date=end)
        return total_saved

    @property
    def _completeness(self) -> CompletenessEngine:
        return CompletenessEngine(CompletenessConfig(
            source_name="stock_share_float",
            entity_class=StockShareFloatEntities,
            date_column="float_date",
            start_date=self.share_float_start_date,
            event_driven=True,
            pull_by_date=lambda td: self.share_float_workflow.pull_share_float_by_float_date(
                float_date=td
            ),
        ))

    def refresh_completeness_snapshot(self, start_date=None, end_date=None) -> int:
        return self._completeness.refresh_snapshot(start_date, end_date)

    def check_complete(self, start_date=None, end_date=None, *, progress_queue=None) -> int:
        return self._completeness.check_complete(start_date, end_date, progress_queue=progress_queue)
