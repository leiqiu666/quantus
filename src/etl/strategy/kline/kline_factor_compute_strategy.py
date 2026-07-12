"""因子计算 Strategy：月份编排 + 增量判定 + 逐月调 Workflow。"""

from __future__ import annotations

from src.common.function import tqdm_iter
from src.research.dataset.kline import KlineDataset
from src.research.factor.load import FactorParquetLoad
from src.research.factor.registry import FactorRegistry
from src.research.factor.workflow import FactorComputeWorkflow


class FactorComputeStrategy:
    def __init__(self) -> None:
        self._workflow = FactorComputeWorkflow()
        self._load = FactorParquetLoad()
        self._dataset = KlineDataset()

    def compute_factor(
        self,
        name: str,
        start_month: str | None = None,
        end_month: str | None = None,
        force: bool = False,
    ) -> int:
        FactorRegistry.auto_discover()
        factor = FactorRegistry.get(name)

        kline_months = self._dataset.list_available_months()
        targets = list(kline_months)
        if start_month:
            targets = [m for m in targets if m >= start_month]
        if end_month:
            targets = [m for m in targets if m <= end_month]

        if not force:
            existing = set(self._load.list_existing_months(factor.meta().name))
            targets = [m for m in targets if m not in existing]

        if not targets:
            print(f"因子 {name}：无需计算（已全部覆盖或无可用日K数据）")
            return 0

        total = 0
        for ym in tqdm_iter(targets, desc=f"计算因子 {name}"):
            rows = self._workflow.compute_month(factor, ym)
            total += rows

        print(f"因子 {name}：计算完成，覆盖 {len(targets)} 个月，共 {total} 行")
        return total

    def compute_all_factors(
        self,
        start_month: str | None = None,
        end_month: str | None = None,
        force: bool = False,
    ) -> int:
        FactorRegistry.auto_discover()
        total = 0
        for meta in FactorRegistry.list_all():
            rows = self.compute_factor(meta.name, start_month, end_month, force)
            total += rows
        return total
