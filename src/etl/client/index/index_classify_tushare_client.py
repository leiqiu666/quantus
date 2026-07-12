"""Tushare 申万行业分类 Client。"""

from __future__ import annotations

import pandas as pd

from src.common.function import create_rate_limiter
from src.common.tushare_client import TushareClient
from src.etl.client.base import call_with_network_retry
from src.etl.client.index.index_classify_common import (
    INDEX_CLASSIFY_COLUMNS,
    INDEX_CLASSIFY_SRC,
    finalize_index_classify,
)

_acquire_index_classify_rate_limit = create_rate_limiter(200)


class TushareIndexClassifyClient:
    def __init__(self) -> None:
        self.tushare_client = TushareClient()
        self.ts = self.tushare_client.ts

    def pull_index_classify(self, *, level: str, src: str = INDEX_CLASSIFY_SRC) -> pd.DataFrame:
        level = (level or "").strip().upper()
        src = (src or INDEX_CLASSIFY_SRC).strip()
        if not level:
            return pd.DataFrame()

        _acquire_index_classify_rate_limit()
        df = call_with_network_retry(
            self.ts.index_classify,
            level=level,
            src=src,
            fields=",".join(INDEX_CLASSIFY_COLUMNS),
        )
        out = finalize_index_classify(df)
        if not out.empty and "src" in out.columns:
            out["src"] = src
        return out
