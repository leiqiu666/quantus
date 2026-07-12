from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Tuple, Type

import pandas as pd

from src.common.database import Database
from src.common.function import dataframe_to_list
from src.entities.data_entities.financial.financial_report_balance_entities import ReportBalanceEntities
from src.entities.data_entities.financial.financial_report_cashflow_entities import ReportCashflowEntities
from src.entities.data_entities.financial.financial_report_income_entities import ReportIncomeEntities
from src.entities.data_entities.financial.financial_report_indicator_entities import ReportIndicatorEntities
from src.entities.data_entities.financial.financial_report_period_count_entities import ReportPeriodCountEntities
from src.etl.extract.local.financial.financial_report_local_extract import ReportExtract as LocalReportExtract

DEFAULT_REPORT_MATCH_KEYS: Dict[Type[Any], Tuple[str, ...]] = {
    ReportIncomeEntities: ("ts_code", "end_date", "f_ann_date", "report_type", "update_flag"),
    ReportBalanceEntities: ("ts_code", "end_date", "f_ann_date", "report_type", "update_flag"),
    ReportCashflowEntities: ("ts_code", "end_date", "f_ann_date", "report_type", "update_flag"),
    ReportIndicatorEntities: ("ts_code", "end_date", "ann_date", "update_flag"),
}

_ENTITY_REPORT_TYPE: Dict[Type[Any], str] = {
    ReportIncomeEntities: "income",
    ReportBalanceEntities: "balance",
    ReportCashflowEntities: "cashflow",
    ReportIndicatorEntities: "indicator",
}

COMPARE_SKIP_COLUMNS = frozenset({"id"})


@lru_cache(maxsize=None)
def _entity_column_info(entity: Type[Any]) -> Tuple[Tuple[str, ...], FrozenSet[str]]:
    """返回 (按表序的列名 tuple, 列名集合) — 每个实体仅解析一次。"""
    names = tuple(col.name for col in entity.__table__.columns)
    return names, frozenset(names)


@dataclass(frozen=True)
class LoadReportFilterResult:
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
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, default=str)
    return value


def _record_compare_view(record: Dict[str, Any], column_names: Sequence[str]) -> Dict[str, Any]:
    return {
        name: _normalize_compare_value(record.get(name))
        for name in column_names
        if name not in COMPARE_SKIP_COLUMNS
    }


def _records_equal(
    existing: Dict[str, Any],
    incoming: Dict[str, Any],
    column_names: Sequence[str],
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


class ReportLoad:
    def __init__(self):
        self.db = Database()

    def load_report(
        self,
        entities: Type[Any],
        df: pd.DataFrame,
        *,
        verbose: bool = False,
    ) -> int:
        """
        将清洗后的 DataFrame 批量写入 PostgreSQL。

        Args:
            entities: SQLAlchemy 实体类（表模型），如 ReportIncomeEntities。
            df: 待入库的数据表（DataFrame，列名已为实体字段）。
            verbose: 是否输出调试信息（建议在进度条场景下保持 False）。

        Returns:
            实际写入/更新的记录数。
        """
        if df is None or df.empty:
            if verbose:
                print("[信息] 入库 DataFrame 为空，跳过写入")
            return 0

        records = dataframe_to_list(df)

        saved_count = self.db.bulk_upsert_postgresql(
            model_class=entities,
            records=records,
            conflict_keys=None,
            fallback_on_error=True,
        )

        return saved_count

    def load_report_filter(
        self,
        entities: Type[Any],
        df: pd.DataFrame,
        *,
        scope_end_date: str,
        local_report_extract: LocalReportExtract,
        match_keys: Optional[Sequence[str]] = None,
        verbose: bool = False,
    ) -> LoadReportFilterResult:
        """
        先按报告期查库（LocalExtract → Service → Model），行级比对后 insert / update / skip。

        规格：spec/load/存储-先查再改再插.sdd.md
        """
        if df is None or df.empty:
            if verbose:
                print("[load_report_filter] DataFrame 为空，跳过")
            return LoadReportFilterResult(0, 0, 0)

        keys = tuple(match_keys or DEFAULT_REPORT_MATCH_KEYS.get(entities, ()))
        if not keys:
            raise ValueError(f"未配置 {entities.__name__} 的 match_keys")

        report_type = _ENTITY_REPORT_TYPE.get(entities)
        if report_type is None:
            raise ValueError(f"load_report_filter 不支持的实体: {entities.__name__}")

        incoming_records = dataframe_to_list(df)
        column_names, valid_columns = _entity_column_info(entities)

        existing_rows = local_report_extract.get_report_rows_by_end_date(
            report_type, str(scope_end_date)
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
            if str(record.get("end_date", "")) != str(scope_end_date):
                scope_mismatch += 1
                skipped += 1
                continue

            key = _match_key(record, keys)
            existing = index.get(key)
            if existing is None:
                to_insert.append(record)
                continue
            if _records_equal(existing, record, column_names):
                skipped += 1
                continue
            record["id"] = existing["id"]
            to_update.append(record)

        inserted = len(to_insert)
        updated = 0
        if to_insert:
            self.db.bulk_upsert_postgresql(
                entities,
                to_insert,
                conflict_keys=list(keys),
                fallback_on_error=True,
            )
        if to_update:
            updated = self.db.bulk_update(entities, to_update)

        if verbose:
            print(
                f"[load_report_filter] scope_end_date={scope_end_date} "
                f"incoming={len(incoming_records)} inserted={inserted} "
                f"updated={updated} skipped={skipped} scope_mismatch={scope_mismatch}"
            )

        return LoadReportFilterResult(inserted=inserted, updated=updated, skipped=skipped)

    def load_report_period_count(
        self,
        records: list[dict[str, Any]],
        *,
        verbose: bool = False,
    ) -> int:
        """
        批量写入 / 更新 report_period_count（按 report_period upsert）。
        """
        if not records:
            if verbose:
                print("[信息] report_period_count 记录为空，跳过写入")
            return 0
        return self.db.bulk_upsert_postgresql(
            model_class=ReportPeriodCountEntities,
            records=records,
            conflict_keys=["report_period"],
            fallback_on_error=True,
        )
