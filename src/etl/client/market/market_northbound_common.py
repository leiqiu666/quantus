"""沪深股通十大成交股 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

HSGT_TOP10_COLUMNS: tuple[str, ...] = (
    "trade_date", "ts_code", "name", "close", "change",
    "rank", "market_type", "amount", "net_amount", "buy", "sell",
)

_NUMERIC_COLS = ("close", "change", "rank", "market_type", "amount", "net_amount", "buy", "sell")


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def finalize_hsgt_top10(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()

    if "ts_code" in out.columns:
        out["ts_code"] = out["ts_code"].astype(str).str.strip()
    if "trade_date" in out.columns:
        out["trade_date"] = out["trade_date"].map(_normalize_ymd)
    if "name" in out.columns:
        out["name"] = out["name"].astype(str).str.strip()
        out.loc[out["name"].isin(["nan", "None", ""]), "name"] = ""

    for col in _NUMERIC_COLS:
        if col in out.columns:
            out[col] = out[col].replace({pd.NA: None, float("nan"): None})

    out = out[out["trade_date"].astype(str).str.len() == 8]

    for col in HSGT_TOP10_COLUMNS:
        if col not in out.columns:
            if col in ("ts_code", "trade_date", "name"):
                out[col] = ""
            else:
                out[col] = pd.NA

    return out[list(HSGT_TOP10_COLUMNS)].reset_index(drop=True)
