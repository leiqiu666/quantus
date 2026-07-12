"""指数成分权重 Extract。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.index.index_weight_tushare_client import TushareIndexWeightClient


class IndexWeightExtract:
    def __init__(self) -> None:
        self._client = TushareIndexWeightClient()

    def pull_index_weight(
        self, *, index_code: str, start_date: str, end_date: str,
    ) -> pd.DataFrame:
        return self._client.pull_index_weight(
            index_code=index_code, start_date=start_date, end_date=end_date,
        )
