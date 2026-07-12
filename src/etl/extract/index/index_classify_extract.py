"""申万行业分类 Extract。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.index.index_classify_common import INDEX_CLASSIFY_LEVELS, INDEX_CLASSIFY_SRC
from src.etl.client.index.index_classify_tushare_client import TushareIndexClassifyClient


class IndexClassifyExtract:
    def __init__(self) -> None:
        self._client = TushareIndexClassifyClient()

    def pull_index_classify_snapshot(self) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for level in INDEX_CLASSIFY_LEVELS:
            df = self._client.pull_index_classify(level=level, src=INDEX_CLASSIFY_SRC)
            if df is not None and not df.empty:
                frames.append(df)
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)
