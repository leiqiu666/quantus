"""申万行业成分 Extract。"""

from __future__ import annotations

import pandas as pd

from src.common.database import Database
from src.entities.data_entities.index.index_classify_entities import IndexClassifyEntities
from src.etl.client.index.index_classify_common import INDEX_CLASSIFY_SRC
from src.etl.client.index.index_member_all_tushare_client import TushareIndexMemberAllClient


class IndexMemberAllExtract:
    def __init__(self) -> None:
        self._client = TushareIndexMemberAllClient()
        self._db = Database()

    def _list_l1_codes(self) -> list[str]:
        session = self._db.get_session()
        try:
            rows = (
                session.query(IndexClassifyEntities.industry_code)
                .filter_by(level="L1", src=INDEX_CLASSIFY_SRC)
                .all()
            )
            codes = sorted({str(r[0]).strip() for r in rows if r[0]})
            if codes:
                return codes
        finally:
            session.close()
        return []

    def pull_index_member_all_snapshot(self) -> pd.DataFrame:
        l1_codes = self._list_l1_codes()
        frames: list[pd.DataFrame] = []
        if l1_codes:
            for l1_code in l1_codes:
                df = self._client.pull_index_member_all(l1_code=l1_code, is_new="Y")
                if df is not None and not df.empty:
                    frames.append(df)
        else:
            df = self._client.pull_index_member_all(is_new="Y")
            if df is not None and not df.empty:
                frames.append(df)
        if not frames:
            return pd.DataFrame()
        merged = pd.concat(frames, ignore_index=True)
        key_cols = ["ts_code", "l1_code", "l2_code", "l3_code", "in_date"]
        return merged.drop_duplicates(subset=key_cols, keep="first").reset_index(drop=True)
