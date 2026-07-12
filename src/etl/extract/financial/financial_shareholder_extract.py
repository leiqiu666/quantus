"""前十大股东 Extract：编排 Tushare Client。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.financial.financial_shareholder_tushare_client import TushareShareholderClient


class ShareholderExtract:
    def __init__(self) -> None:
        self._client = TushareShareholderClient()

    def pull_top10_by_ann_date(self, *, ann_date: str) -> pd.DataFrame:
        return self._client.pull_top10_holders_by_ann_date(ann_date=ann_date)
