from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from src.common.database import Database, DEFAULT_BULK_UPSERT_CHUNK_SIZE
from src.common.function import dataframe_to_list
from src.entities.data_entities.kline.kline_daily_entities import KlineDailyEntities
from src.entities.data_entities.kline.kline_daily_period_count_entities import (
    KlineDailyPeriodCountEntities,
)
from src.etl.client.kline.kline_common import KLINE_DAILY_SATELLITE_COLUMNS
from src.etl.extract.local.kline.kline_local_extract import KlineLocalExtract

DEFAULT_KLINE_DAILY_MATCH_KEYS: Tuple[str, ...] = ("ts_code", "trade_date")
COMPARE_SKIP_COLUMNS = frozenset({"id"})


@lru_cache(maxsize=1)
def _kline_daily_columns() -> Tuple[Tuple[str, ...], FrozenSet[str], Tuple[str, ...]]:
    """返回 (按表序的列名 tuple, 列名集合, 全量 upsert 时的 update_columns)。"""
    names = tuple(col.name for col in KlineDailyEntities.__table__.columns)
    update_cols = tuple(
        n
        for n in names
        if n not in ("id", "ts_code", "trade_date", *KLINE_DAILY_SATELLITE_COLUMNS)
    )
    return names, frozenset(names), update_cols


KLINE_DAILY_UPSERT_COLUMNS: Tuple[str, ...] = _kline_daily_columns()[2]


@dataclass(frozen=True)
class LoadKlineDailyFilterResult:
    inserted: int
    updated: int
    skipped: int

    @property
    def total_written(self) -> int:
        return self.inserted + self.updated


def _match_key(record: Dict[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    return tuple("" if record.get(k) is None else str(record.get(k)) for k in keys)


def _normalize_compare_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return value
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def _record_compare_view(record: Dict[str, Any], column_names: Iterable[str]) -> Dict[str, Any]:
    return {
        name: _normalize_compare_value(record.get(name))
        for name in column_names
        if name not in COMPARE_SKIP_COLUMNS
    }


def _records_equal(
    existing: Dict[str, Any],
    incoming: Dict[str, Any],
    column_names: Iterable[str],
) -> bool:
    left = _record_compare_view(existing, column_names)
    right = _record_compare_view(incoming, column_names)
    if set(left.keys()) != set(right.keys()):
        return False
    for key in left:
        lv, rv = left[key], right[key]
        if isinstance(lv, float) and isinstance(rv, float):
            if not math.isclose(lv, rv, rel_tol=0.0, abs_tol=1e-9):
                return False
        elif lv != rv:
            return False
    return True


class KlineLoad:
    def __init__(self):
        self.db = Database()

    def load_kline_daily(
        self,
        df: pd.DataFrame,
        *,
        chunk_size: int | None = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
        update_on_conflict: bool = True,
    ) -> int:
        if df is None or df.empty:
            return 0
        records = dataframe_to_list(df)
        return self.db.bulk_upsert_postgresql(
            model_class=KlineDailyEntities,
            records=records,
            conflict_keys=["ts_code", "trade_date"],
            fallback_on_error=True,
            skip_length_check=True,
            chunk_size=chunk_size,
            update_on_conflict=update_on_conflict,
            update_columns=list(KLINE_DAILY_UPSERT_COLUMNS),
        )

    def _load_kline_daily_partial(
        self,
        df: pd.DataFrame,
        *,
        select_columns: FrozenSet[str],
        update_columns: List[str],
        chunk_size: int | None,
    ) -> int:
        """卫星列 upsert 通用实现：只保留指定列，仅在冲突时更新指定列。"""
        if df is None or df.empty:
            return 0
        records = [
            {k: v for k, v in raw.items() if k in select_columns}
            for raw in dataframe_to_list(df)
        ]
        if not records:
            return 0
        self.db.bulk_upsert_postgresql(
            model_class=KlineDailyEntities,
            records=records,
            conflict_keys=["ts_code", "trade_date"],
            fallback_on_error=True,
            chunk_size=chunk_size,
            update_columns=update_columns,
        )
        return len(records)

    def load_kline_adj_factor(
        self,
        df: pd.DataFrame,
        *,
        chunk_size: int | None = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
    ) -> int:
        """将复权因子 upsert 至 kline_daily.adj_factor（冲突时仅更新 adj_factor）。"""
        return self._load_kline_daily_partial(
            df,
            select_columns=frozenset({"ts_code", "trade_date", "adj_factor"}),
            update_columns=["adj_factor"],
            chunk_size=chunk_size,
        )

    def load_kline_stk_limit(
        self,
        df: pd.DataFrame,
        *,
        chunk_size: int | None = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
    ) -> int:
        """将涨跌停价 upsert 至 kline_daily.up_limit/down_limit（冲突时仅更新这两列）。"""
        return self._load_kline_daily_partial(
            df,
            select_columns=frozenset({"ts_code", "trade_date", "up_limit", "down_limit"}),
            update_columns=["up_limit", "down_limit"],
            chunk_size=chunk_size,
        )

    def load_kline_daily_filter(
        self,
        df: pd.DataFrame,
        *,
        scope_trade_date: str,
        local_kline_extract: KlineLocalExtract,
        match_keys: Sequence[str] = DEFAULT_KLINE_DAILY_MATCH_KEYS,
        chunk_size: int | None = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
        verbose: bool = False,
    ) -> LoadKlineDailyFilterResult:
        """先按交易日查库，行级比对后 insert / update / skip。

        规格：spec/load/存储-先查再改再插.sdd.md
        """
        if df is None or df.empty:
            if verbose:
                print("[load_kline_daily_filter] DataFrame 为空，跳过")
            return LoadKlineDailyFilterResult(0, 0, 0)

        keys = tuple(match_keys)
        column_names, valid_columns, _ = _kline_daily_columns()
        incoming_records = dataframe_to_list(df)

        existing_rows = local_kline_extract.get_kline_daily_by_trade_date(
            str(scope_trade_date)
        )
        index: Dict[Tuple[str, ...], Dict[str, Any]] = {}
        for row_dict in existing_rows:
            index[_match_key(row_dict, keys)] = row_dict

        to_insert: List[Dict[str, Any]] = []
        to_update: List[Dict[str, Any]] = []
        skipped = 0
        scope_mismatch = 0

        for raw in incoming_records:
            record = {k: v for k, v in raw.items() if k in valid_columns}
            if str(record.get("trade_date", "")) != str(scope_trade_date):
                scope_mismatch += 1
                skipped += 1
                continue

            key = _match_key(record, keys)
            existing = index.get(key)
            compare_columns = [
                name
                for name in column_names
                if name not in COMPARE_SKIP_COLUMNS and name in record
            ]
            if existing is None:
                to_insert.append(record)
                continue
            if _records_equal(existing, record, compare_columns):
                skipped += 1
                continue
            record["id"] = existing["id"]
            for col in KLINE_DAILY_SATELLITE_COLUMNS:
                if col not in record and existing.get(col) is not None:
                    record[col] = existing[col]
            to_update.append(record)

        inserted = len(to_insert)
        updated = 0
        if to_insert:
            self.db.bulk_upsert_postgresql(
                KlineDailyEntities,
                to_insert,
                conflict_keys=list(keys),
                fallback_on_error=True,
                skip_length_check=True,
                chunk_size=chunk_size,
                update_columns=list(KLINE_DAILY_UPSERT_COLUMNS),
            )
        if to_update:
            updated = self.db.bulk_update(KlineDailyEntities, to_update)

        if verbose:
            print(
                f"[load_kline_daily_filter] scope_trade_date={scope_trade_date} "
                f"incoming={len(incoming_records)} inserted={inserted} "
                f"updated={updated} skipped={skipped} scope_mismatch={scope_mismatch}"
            )

        return LoadKlineDailyFilterResult(
            inserted=inserted, updated=updated, skipped=skipped
        )

    def load_kline_daily_period_count(
        self,
        records: list[dict],
        *,
        verbose: bool = False,
    ) -> int:
        """批量写入 / 更新 kline_daily_period_count（按 trade_date upsert）。"""
        if not records:
            if verbose:
                print("[信息] kline_daily_period_count 记录为空，跳过写入")
            return 0
        self.db.ensure_table(KlineDailyPeriodCountEntities)
        return self.db.bulk_upsert_postgresql(
            model_class=KlineDailyPeriodCountEntities,
            records=records,
            conflict_keys=["trade_date"],
            fallback_on_error=True,
        )
