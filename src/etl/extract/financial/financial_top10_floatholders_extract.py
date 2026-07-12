"""前十大流通股东 Extract。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.financial.financial_top10_floatholders_tushare_client import (
    TushareTop10FloatholdersClient,
)


class Top10FloatholdersExtract:
    def __init__(self) -> None:
        self._client = TushareTop10FloatholdersClient()

    def pull_top10_floatholders_by_ann_date(self, *, ann_date: str) -> pd.DataFrame:
        return self._client.pull_top10_floatholders_by_ann_date(ann_date=ann_date)
