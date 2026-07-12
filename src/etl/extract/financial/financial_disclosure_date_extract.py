"""财报披露计划 Extract。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.financial.financial_disclosure_date_tushare_client import (
    TushareDisclosureDateClient,
)


class DisclosureDateExtract:
    def __init__(self) -> None:
        self._client = TushareDisclosureDateClient()

    def pull_disclosure_date_by_period(self, period: str) -> pd.DataFrame:
        return self._client.pull_disclosure_date_by_period(period)
