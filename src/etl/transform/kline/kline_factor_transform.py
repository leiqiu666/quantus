"""Tushare 技术因子 Transform：_hfq 后缀重命名 + NaN 清理。"""

from __future__ import annotations

import pandas as pd

from src.entities.client_entities.tushare_entities import STK_FACTOR_PRO_RENAME


class TushareFactorTransform:
    @staticmethod
    def transform(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()

        rename = {k: v for k, v in STK_FACTOR_PRO_RENAME.items() if k in df.columns}
        if rename:
            df = df.rename(columns=rename)

        return df
