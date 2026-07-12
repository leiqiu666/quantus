"""股东户数 Workflow。"""

from __future__ import annotations

from src.etl.extract.financial.financial_stock_holder_extract import StkHoldernumberExtract
from src.etl.load.financial.financial_stock_holder_load import StkHoldernumberLoad


class StkHoldernumberWorkflow:
    def __init__(self) -> None:
        self.extract = StkHoldernumberExtract()
        self.load = StkHoldernumberLoad()

    def pull_stk_holdernumber_by_ann_date(self, *, ann_date: str) -> int:
        df = self.extract.pull_stk_holdernumber_by_ann_date(ann_date=ann_date)
        return self.load.load_stk_holdernumber(df)

    def pull_stk_holdernumber_by_ts_code(
        self, *, ts_code: str, start_date: str, end_date: str,
    ) -> int:
        df = self.extract.pull_stk_holdernumber_by_ts_code(
            ts_code=ts_code, start_date=start_date, end_date=end_date,
        )
        return self.load.load_stk_holdernumber(df)
