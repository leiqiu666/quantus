"""Tushare 技术因子 Extract：按交易日拉取全市场，超限自动重试。"""

from __future__ import annotations

import time

import pandas as pd

from src.etl.client.kline.kline_factor_tushare_client import TushareFactorClient

_MAX_RETRIES = 3
_RETRY_WAIT = 65


class TushareFactorExtract:
    def __init__(self) -> None:
        self._client = TushareFactorClient()

    def pull_by_date(self, trade_date: str) -> pd.DataFrame:
        for attempt in range(_MAX_RETRIES):
            try:
                return self._client.pull_by_date(trade_date)
            except Exception as e:
                msg = str(e).lower()
                if "freq" in msg or "limit" in msg or "exceed" in msg or "最多" in msg:
                    print(f"[超限重试] {trade_date} 第{attempt + 1}次，等待 {_RETRY_WAIT}s")
                    time.sleep(_RETRY_WAIT)
                    continue
                raise
        return self._client.pull_by_date(trade_date)
