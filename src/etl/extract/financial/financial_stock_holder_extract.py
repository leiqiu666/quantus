"""股东户数 Extract。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.financial.financial_stock_holder_tushare_client import TushareStkHolderClient


class StkHoldernumberExtract:
    def __init__(self) -> None:
        self._client = TushareStkHolderClient()

    def pull_stk_holdernumber_by_ann_date(
        self, *, ann_date: str,
    ) -> pd.DataFrame:
        return self._client.pull_stk_holdernumber_by_ann_date(ann_date=ann_date)

    def pull_stk_holdernumber_by_ts_code(
        self, *, ts_code: str, start_date: str, end_date: str,
    ) -> pd.DataFrame:
        return self._client.pull_stk_holdernumber_by_ts_code(
            ts_code=ts_code, start_date=start_date, end_date=end_date,
        )
