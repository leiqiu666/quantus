"""指数日线 Client 共用工具。"""

from __future__ import annotations

import pandas as pd

from src.etl.client.index.index_weight_common import INDEX_CODES

INDEX_DAILY_COLUMNS: tuple[str, ...] = (
    "ts_code",
    "trade_date",
    "close",
    "open",
    "high",
    "low",
    "pre_close",
    "change",
    "pct_chg",
    "vol",
    "amount",
)

MAJOR_BENCHMARK_CODES: tuple[str, ...] = (
    "000001.SH",
    "399001.SZ",
    "000016.SH",
    "000688.SH",
    "399005.SZ",
)


def _normalize_ymd(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip().replace("-", "")
    return s[:8] if len(s) >= 8 else ""


def resolve_index_daily_codes() -> tuple[str, ...]:
    codes = set(INDEX_CODES) | set(MAJOR_BENCHMARK_CODES)
    try:
        from src.common.database import Database
        from src.entities.data_entities.index.index_basic_entities import IndexBasicEntities

        session = Database().get_session()
        try:
            rows = (
                session.query(IndexBasicEntities.ts_code)
                .filter(IndexBasicEntities.market.in_(("CSI", "SSE")))
                .filter(IndexBasicEntities.category == "综合指数")
                .all()
            )
            for row in rows:
                code = str(row[0] or "").strip()
                if code:
                    codes.add(code)
        finally:
            session.close()
    except Exception:
        pass
    return tuple(sorted(codes))


def finalize_index_daily(df: pd.DataFrame | None) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    if "ts_code" in out.columns:
        out["ts_code"] = out["ts_code"].astype(str).str.strip()
    if "trade_date" in out.columns:
        out["trade_date"] = out["trade_date"].map(_normalize_ymd)

    float_cols = (
        "close",
        "open",
        "high",
        "low",
        "pre_close",
        "change",
        "pct_chg",
        "vol",
        "amount",
    )
    for col in float_cols:
        if col in out.columns:
            out[col] = out[col].replace({pd.NA: None, float("nan"): None})

    out = out[out["trade_date"].astype(str).str.len() == 8]

    for col in INDEX_DAILY_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA if col not in ("ts_code", "trade_date") else ""

    return out[list(INDEX_DAILY_COLUMNS)].reset_index(drop=True)
