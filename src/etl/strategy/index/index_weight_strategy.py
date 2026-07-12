"""指数成分权重 Strategy：按月 × 指数遍历。"""

from __future__ import annotations

import calendar
from datetime import datetime

from src.common.function import tqdm_iter
from src.common.setting import settings
from src.etl.client.index.index_weight_common import INDEX_CODES
from src.etl.extract.local.index.index_weight_local_extract import IndexWeightLocalExtract
from src.etl.workflow.index.index_weight_workflow import IndexWeightWorkflow
from src.common.completeness import CompletenessConfig, CompletenessEngine
from src.entities.data_entities.index.index_weight_entities import IndexWeightEntities


def _month_range(start_ym: str, end_ym: str) -> list[str]:
    """生成 YYYYMM 列表（含两端）。"""
    y, m = int(start_ym[:4]), int(start_ym[4:6])
    ey, em = int(end_ym[:4]), int(end_ym[4:6])
    result = []
    while (y, m) <= (ey, em):
        result.append(f"{y:04d}{m:02d}")
        m += 1
        if m > 12:
            y += 1
            m = 1
    return result


def _month_first_last(ym: str) -> tuple[str, str]:
    y, m = int(ym[:4]), int(ym[4:6])
    first = f"{y:04d}{m:02d}01"
    last_day = calendar.monthrange(y, m)[1]
    last = f"{y:04d}{m:02d}{last_day:02d}"
    return first, last


class IndexWeightStrategy:
    def __init__(self) -> None:
        self.workflow = IndexWeightWorkflow()
        self.local = IndexWeightLocalExtract()
        self.start_month = settings.etl_start_month("index_weight")

    def pull_index_weight_by_month_range(
        self,
        start_month: str | None = None,
        end_month: str | None = None,
    ) -> int:
        if start_month is None:
            start_month = self.start_month
        if end_month is None:
            end_month = datetime.now().strftime("%Y%m")

        floor = (start_month or "").strip()
        end = (end_month or "").strip()
        if not floor or not end or floor > end:
            return 0

        eff_start = self.local.resolve_incremental_start_month(configured_start_month=floor)
        if not eff_start or eff_start > end:
            max_td = self.local.get_max_trade_date()
            print(f"[信息] index_weight 已同步至 {max_td or '无'}，跳过")
            return 0

        months = _month_range(eff_start, end)
        tasks = [(m, ic) for m in months for ic in INDEX_CODES]
        if not tasks:
            return 0

        print(f"[信息] {eff_start}~{end} 共 {len(months)} 月 × {len(INDEX_CODES)} 指数 = {len(tasks)} 次拉取")

        self.refresh_completeness_snapshot(start_date=f"{floor}01", end_date=f"{end}31")

        total_saved = 0
        for month, index_code in tqdm_iter(tasks, desc="指数权重入库", unit="次"):
            first, last = _month_first_last(month)
            n = self.workflow.pull_index_weight(
                index_code=index_code, start_date=first, end_date=last,
            )
            total_saved += n

        self.refresh_completeness_snapshot(start_date=f"{floor}01", end_date=f"{end}31")
        return total_saved

    @property
    def _completeness(self) -> CompletenessEngine:
        start_date = f"{self.start_month}01" if self.start_month and len(self.start_month) == 6 else self.start_month
        return CompletenessEngine(CompletenessConfig(
            source_name="index_weight",
            entity_class=IndexWeightEntities,
            date_column="trade_date",
            start_date=start_date,
            pull_by_index=lambda index_code, start_date, end_date: self.workflow.pull_index_weight(
                index_code=index_code, start_date=start_date, end_date=end_date,
            ),
        ))

    def refresh_completeness_snapshot(self, start_date=None, end_date=None) -> int:
        return self._completeness.refresh_snapshot(start_date, end_date)

    def check_complete(self, start_date=None, end_date=None, *, progress_queue=None) -> int:
        return self._completeness.check_complete_per_index(
            start_date, end_date, progress_queue=progress_queue,
        )
