"""主营业务构成 Extract。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.financial.financial_fina_mainbz_tushare_client import (
    TushareFinaMainbzClient,
)


class FinaMainbzExtract:
    def __init__(self) -> None:
        self._client = TushareFinaMainbzClient()

    def pull_fina_mainbz_period(self, period: str) -> pd.DataFrame:
        return self._client.pull_fina_mainbz_vip_by_period(period)
