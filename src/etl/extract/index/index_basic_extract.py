"""指数基本信息 Extract。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.index.index_basic_tushare_client import TushareIndexBasicClient


class IndexBasicExtract:
    def __init__(self) -> None:
        self._client = TushareIndexBasicClient()

    def pull_index_basic_snapshot(self) -> pd.DataFrame:
        return self._client.pull_index_basic_all_markets()
