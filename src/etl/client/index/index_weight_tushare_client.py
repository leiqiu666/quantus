"""Tushare 指数成分权重 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.index.index_weight_common import INDEX_WEIGHT_COLUMNS, finalize_index_weight

_acquire_index_weight_rate_limit = create_rate_limiter(200)


class TushareIndexWeightClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_index_weight(
        self,
        *,
        index_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        if not (index_code or "").strip():
            return pd.DataFrame()

        _acquire_index_weight_rate_limit()
        df = call_with_network_retry(
            self.ts.index_weight,
            index_code=index_code,
            start_date=start_date,
            end_date=end_date,
            fields=",".join(INDEX_WEIGHT_COLUMNS),
        )
        return finalize_index_weight(df)
