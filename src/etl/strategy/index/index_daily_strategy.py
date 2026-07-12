"""指数日线 Strategy：逐指数 × 交易日完整性。"""

from __future__ import annotations

from datetime import datetime

from src.common.completeness import CompletenessConfig, CompletenessEngine
from src.common.function import tqdm_iter
from src.common.setting import settings
from src.entities.data_entities.index.index_daily_entities import IndexDailyEntities
from src.etl.client.index.index_daily_common import resolve_index_daily_codes
from src.etl.extract.local.index.index_daily_local_extract import IndexDailyLocalExtract
from src.etl.strategy.stock.stock_trade_calendar_strategy import TradeCalStrategy
from src.etl.workflow.index.index_daily_workflow import IndexDailyWorkflow


class IndexDailyStrategy:
    def __init__(self) -> None:
        self.workflow = IndexDailyWorkflow()
        self.local = IndexDailyLocalExtract()
        self.trade_cal_strategy = TradeCalStrategy()
        self.start_date = settings.etl_start_date("index_daily")

    def pull_index_daily_by_code_range(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        *,
        ts_code: str | None = None,
    ) -> int:
        if start_date is None:
            start_date = self.start_date
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        floor = (start_date or "").strip()
        end = (end_date or "").strip()
        if not floor or not end or floor > end:
            return 0

        codes = [ts_code.strip()] if (ts_code or "").strip() else list(resolve_index_daily_codes())
        if not codes:
            return 0

        self.trade_cal_strategy.ensure_trade_cal(
            start_date=floor,
            end_date=end,
            exchange="SSE",
        )

        tasks: list[tuple[str, str, str]] = []
        for code in codes:
            eff_start = self.local.resolve_incremental_start_date(
                ts_code=code,
                configured_start_date=floor,
            )
            if not eff_start or eff_start > end:
                continue
            tasks.append((code, eff_start, end))

        if not tasks:
            print(f"[信息] index_daily 已同步至 {end}，跳过")
            return 0

        print(f"[信息] index_daily 共 {len(tasks)} 个指数待补拉")

        self.refresh_completeness_snapshot(start_date=floor, end_date=end)

        total_saved = 0
        for code, eff_start, eff_end in tqdm_iter(tasks, desc="指数日线入库", unit="指数"):
            n = self.workflow.pull_index_daily(
                ts_code=code,
                start_date=eff_start,
                end_date=eff_end,
            )
            total_saved += n

        self.refresh_completeness_snapshot(start_date=floor, end_date=end)
        return total_saved

    @property
    def _completeness(self) -> CompletenessEngine:
        return CompletenessEngine(CompletenessConfig(
            source_name="index_daily",
            entity_class=IndexDailyEntities,
            date_column="trade_date",
            start_date=self.start_date,
            index_codes=resolve_index_daily_codes(),
            index_column="ts_code",
            index_date_unit="day",
            pull_by_index=lambda index_code, start_date, end_date: self.workflow.pull_index_daily(
                ts_code=index_code,
                start_date=start_date,
                end_date=end_date,
            ),
        ))

    def refresh_completeness_snapshot(self, start_date=None, end_date=None) -> int:
        return self._completeness.refresh_snapshot(start_date, end_date)

    def check_complete(self, start_date=None, end_date=None, *, progress_queue=None) -> int:
        return self._completeness.check_complete_per_index(
            start_date, end_date, progress_queue=progress_queue,
        )
