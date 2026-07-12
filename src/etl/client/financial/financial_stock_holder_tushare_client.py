"""Tushare 股东户数 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.financial.financial_stock_holder_common import STK_HOLDERNUMBER_COLUMNS, finalize_stk_holdernumber

_acquire_stk_holder_rate_limit = create_rate_limiter(100)

_PAGE_SIZE = 3000


class TushareStkHolderClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_stk_holdernumber_by_ann_date(self, *, ann_date: str) -> pd.DataFrame:
        ad = (ann_date or "").strip()
        if not ad:
            return pd.DataFrame()

        frames: list[pd.DataFrame] = []
        offset = 0
        while True:
            _acquire_stk_holder_rate_limit()
            page = call_with_network_retry(
                self.ts.stk_holdernumber,
                ann_date=ad,
                fields=",".join(STK_HOLDERNUMBER_COLUMNS),
                offset=offset,
                limit=_PAGE_SIZE,
            )
            if page is None or page.empty:
                break
            frames.append(page)
            if len(page) < _PAGE_SIZE:
                break
            offset += _PAGE_SIZE

        if not frames:
            return pd.DataFrame()

        return finalize_stk_holdernumber(pd.concat(frames, ignore_index=True))

    def pull_stk_holdernumber_by_ts_code(
        self,
        *,
        ts_code: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        if not (ts_code or "").strip():
            return pd.DataFrame()

        _acquire_stk_holder_rate_limit()
        df = call_with_network_retry(
            self.ts.stk_holdernumber,
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields=",".join(STK_HOLDERNUMBER_COLUMNS),
        )
        return finalize_stk_holdernumber(df)
