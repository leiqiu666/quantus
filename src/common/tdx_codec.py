"""通达信 tq 返回值与 JSON 互转，供 API 与 HTTP Client 共用。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd

_DATAFRAME_TYPE = "dataframe"


def _json_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if np.isnan(value):
            return None
        return value
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        fv = float(value)
        return None if np.isnan(fv) else fv
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return pd.Timestamp(value).isoformat()
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"无法序列化为 JSON 标量: {type(value)!r}")


def serialize_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    split = df.to_dict(orient="split")
    return {
        "__type__": _DATAFRAME_TYPE,
        "index": [_json_scalar(v) for v in split.get("index", [])],
        "columns": [str(c) for c in split.get("columns", [])],
        "data": [
            [_json_scalar(cell) for cell in row]
            for row in split.get("data", [])
        ],
    }


def deserialize_dataframe(payload: dict[str, Any]) -> pd.DataFrame:
    index = payload.get("index", [])
    columns = payload.get("columns", [])
    data = payload.get("data", [])
    if not index and not data:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(data, columns=columns, index=index)
    if index:
        try:
            df.index = pd.to_datetime(df.index)
        except (ValueError, TypeError):
            pass
    return df


def serialize_tq_result(obj: Any) -> Any:
    if isinstance(obj, pd.DataFrame):
        return serialize_dataframe(obj)
    if isinstance(obj, dict):
        return {str(k): serialize_tq_result(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serialize_tq_result(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, (np.integer, np.floating, np.bool_)):
        return _json_scalar(obj)
    if isinstance(obj, (datetime, date, pd.Timestamp)):
        return _json_scalar(obj)
    raise TypeError(f"不支持的 tq 返回值类型: {type(obj)!r}")


def deserialize_tq_result(obj: Any) -> Any:
    if isinstance(obj, dict):
        if obj.get("__type__") == _DATAFRAME_TYPE:
            return deserialize_dataframe(obj)
        return {k: deserialize_tq_result(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [deserialize_tq_result(v) for v in obj]
    return obj


def parse_market_data_payload(payload: Any) -> dict[str, pd.DataFrame]:
    """反序列化 get_market_data 响应并过滤为 DataFrame 字典。"""
    raw = deserialize_tq_result(payload)
    if not raw:
        return {}
    if not isinstance(raw, dict):
        raise RuntimeError(f"get_market_data 响应格式异常: {type(raw)!r}")
    if "error" in raw:
        msg = raw.get("msg", raw.get("error"))
        raise RuntimeError(f"通达信 get_market_data 失败: {msg}")
    return {k: v for k, v in raw.items() if isinstance(v, pd.DataFrame)}
