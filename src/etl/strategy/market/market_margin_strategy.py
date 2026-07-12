"""融资融券明细 Strategy：95% 完整性守门。"""

from __future__ import annotations

from datetime import datetime

from src.common.function import tqdm_iter
from src.common.setting import settings
from src.etl.strategy.stock.stock_trade_calendar_strategy import TradeCalStrategy
from src.etl.extract.local.market.market_margin_local_extract import MarginLocalExtract
from src.etl.workflow.market.market_margin_workflow import MarginWorkflow
from src.common.completeness import CompletenessConfig, CompletenessEngine
from src.entities.data_entities.market.market_margin_entities import MarginDetailEntities


class MarginStrategy:
    def __init__(self) -> None:
        self.margin_workflow = MarginWorkflow()
        self.margin_local = MarginLocalExtract()
        self.trade_cal_strategy = TradeCalStrategy()
        self.margin_start_date = settings.etl_start_date("market_margin_detail")

    def pull_margin_detail_by_date_range(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        if start_date is None:
            start_date = self.margin_start_date
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        floor = (start_date or "").strip()
        end = (end_date or "").strip()
        if not floor or not end or floor > end:
            return 0

        self.trade_cal_strategy.ensure_trade_cal(
            start_date=floor, end_date=end, exchange="SSE",
        )

        pending = self._completeness.backfill_keys(floor, end)
        if not pending:
            print(f"[信息] {floor}~{end} margin_detail 已完整（≥95%），跳过")
            return 0

        print(
            f"[信息] {floor}~{end} 共 {len(pending)} 个开市日待补"
            f"（首日 {pending[0]}，末日 {pending[-1]}）"
        )

        total_saved = 0
        for td in tqdm_iter(pending, desc="融资融券明细入库", unit="日"):
            n = self.margin_workflow.pull_margin_detail_by_date(trade_date=td)
            total_saved += n

        self.refresh_completeness_snapshot(start_date=floor, end_date=end)
        return total_saved

    @property
    def _completeness(self) -> CompletenessEngine:
        local = self.margin_local

        def _margin_universe_size(stock_rows, date_key: str) -> int:
            peak = local.get_peak_daily_universe_count(end_date=date_key)
            if peak > 0:
                return peak
            return len(stock_rows)

        return CompletenessEngine(CompletenessConfig(
            source_name="market_margin_detail",
            entity_class=MarginDetailEntities,
            date_column="trade_date",
            start_date=self.margin_start_date,
            period_stock_count_fn=_margin_universe_size,
            pull_by_date=lambda td: self.margin_workflow.pull_margin_detail_by_date(trade_date=td),
        ))

    def refresh_completeness_snapshot(self, start_date=None, end_date=None) -> int:
        return self._completeness.refresh_snapshot(start_date, end_date)

    def check_complete(self, start_date=None, end_date=None, *, progress_queue=None) -> int:
        return self._completeness.check_complete(start_date, end_date, progress_queue=progress_queue)
