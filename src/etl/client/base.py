"""Client 层通用工具：数据源列名 -> 实体列名映射 + 网络重试。"""

from __future__ import annotations

import sys
import time
from typing import Any, Callable, Type

import pandas as pd
from requests.exceptions import ConnectionError, Timeout

from src.common.setting import settings


def call_with_network_retry(
    fn: Callable[..., Any],
    *args: Any,
    interval: int | None = None,
    max_retries: int | None = None,
    **kwargs: Any,
) -> Any:
    """网络断连时自动重试（DNS 失败 / 连接超时），最多 max_retries 次，每次间隔 interval 秒。"""
    if interval is None:
        interval = settings.tushare_retry_interval
    if max_retries is None:
        max_retries = settings.tushare_retry_max
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except (ConnectionError, Timeout) as exc:
            if attempt + 1 >= max_retries:
                raise
            print(
                f"\n[网络异常] {type(exc).__name__}，{interval}s 后重试 ({attempt + 1}/{max_retries})...",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(interval)


def identity_column_map(*columns: str) -> dict[str, str]:
    """生成 1:1 列名映射（数据源字段与实体字段同名）。"""
    return {col: col for col in columns}


def get_entity_column_names(
    model_class: Type[Any],
    *,
    exclude: frozenset[str] | None = None,
) -> list[str]:
    """获取 SQLAlchemy 实体表列名（默认排除主键 id）。"""
    skip = exclude or frozenset({"id"})
    return [col.name for col in model_class.__table__.columns if col.name not in skip]


def map_dataframe_columns(
    df: pd.DataFrame,
    column_map: dict[str, str],
) -> pd.DataFrame:
    """
    按映射重命名 DataFrame 列（不丢弃未映射列）。

    Args:
        df: 待转换 DataFrame（列名为数据源字段）。
        column_map: 数据源字段 -> 实体字段。
    """
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    rename = {
        src: dst
        for src, dst in column_map.items()
        if src in df.columns and src != dst
    }
    if not rename:
        return df.copy()
    return df.rename(columns=rename)


def apply_source_column_map(
    df: pd.DataFrame,
    column_map: dict[str, str],
) -> pd.DataFrame:
    """
    Client 层入口：将数据源字段映射为实体字段名。

    仅重命名 column_map 中定义的列，保留其余列（供 Transform 写入 JSONB 等）。
    """
    return map_dataframe_columns(df, column_map)


def align_dataframe_to_entity(
    df: pd.DataFrame,
    model_class: Type[Any],
    column_map: dict[str, str],
) -> pd.DataFrame:
    """
    将数据源 DataFrame 映射并对齐到实体表结构。

    1. 按 column_map 重命名列
    2. 丢弃实体中不存在的列
    3. 按实体列顺序输出（仅保留 df 中已有的实体列）
    """
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    mapped = map_dataframe_columns(df, column_map)
    entity_cols = get_entity_column_names(model_class)
    keep = [col for col in entity_cols if col in mapped.columns]
    if not keep:
        return mapped.iloc[0:0].copy()

    extra = [col for col in mapped.columns if col not in entity_cols]
    if extra:
        mapped = mapped.drop(columns=extra)
    return mapped[keep].copy()
