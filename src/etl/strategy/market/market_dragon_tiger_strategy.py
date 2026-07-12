"""龙虎榜 Strategy：按 SSE 开市日逐日拉取、95% 完整性守门。"""

from __future__ import annotations

from datetime import datetime

from src.common.function import tqdm_iter
from src.common.setting import settings
from src.etl.strategy.stock.stock_trade_calendar_strategy import TradeCalStrategy
from src.etl.workflow.market.market_dragon_tiger_workflow import DragonTigerWorkflow
from src.common.completeness import CompletenessConfig, CompletenessEngine
from src.entities.data_entities.market.market_dragon_tiger_list_entities import TopListEntities


class DragonTigerStrategy:
    def __init__(self) -> None:
        self.dragon_tiger_workflow = DragonTigerWorkflow()
        self.trade_cal_strategy = TradeCalStrategy()
        self.dragon_tiger_start_date = settings.etl_start_date("market_dragon_tiger")

    def pull_dragon_tiger_by_date_range(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[int, int]:
        if start_date is None:
            start_date = self.dragon_tiger_start_date
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        floor = (start_date or "").strip()
        end = (end_date or "").strip()
        if not floor or not end or floor > end:
            return 0, 0

        self.trade_cal_strategy.ensure_trade_cal(
            start_date=floor,
            end_date=end,
            exchange="SSE",
        )

        pending = self._completeness.backfill_keys(floor, end)
        if not pending:
            print(f"[信息] {floor}~{end} dragon_tiger 已完整（≥95%），跳过")
            return 0, 0

        print(
            f"[信息] {floor}~{end} 共 {len(pending)} 个开市日待补"
            f"（首日 {pending[0]}，末日 {pending[-1]}）"
        )

        total_list = 0
        total_inst = 0
        pbar = tqdm_iter(pending, desc="龙虎榜入库", unit="日")
        for td in pbar:
            list_count, inst_count = self.dragon_tiger_workflow.pull_dragon_tiger_by_date(td)
            total_list += list_count
            total_inst += inst_count
            pbar.set_postfix(list=list_count, inst=inst_count, date=td)

        self.refresh_completeness_snapshot(start_date=floor, end_date=end)
        return total_list, total_inst

    @property
    def _completeness(self) -> CompletenessEngine:
        return CompletenessEngine(CompletenessConfig(
            source_name="dragon_tiger",
            entity_class=TopListEntities,
            date_column="trade_date",
            start_date=self.dragon_tiger_start_date,
            pull_by_date=lambda td: sum(self.dragon_tiger_workflow.pull_dragon_tiger_by_date(td)),
        ))

    def refresh_completeness_snapshot(self, start_date=None, end_date=None) -> int:
        return self._completeness.refresh_snapshot(start_date, end_date)

    def check_complete(self, start_date=None, end_date=None, *, progress_queue=None) -> int:
        return self._completeness.check_complete(start_date, end_date, progress_queue=progress_queue)
