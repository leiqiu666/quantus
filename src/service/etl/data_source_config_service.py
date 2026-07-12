"""数据源优先级配置：DB 主读 + .env 兜底。"""

from __future__ import annotations

from typing import Iterable

from sqlalchemy.exc import ProgrammingError, OperationalError
from sqlalchemy.orm import Session

from src.common.database import Database
from src.common.setting import settings
from src.entities.data_entities.data_source_config_entities import DataSourceConfigEntities

# data_key -> settings 字段名（表为空时的兜底）
_SETTINGS_FALLBACK: dict[str, str] = {
    "kline_daily": "kline_daily_sources",
    "kline_daily_by_date": "kline_daily_by_date_sources",
    "kline_adj_factor": "kline_adj_factor_sources",
    "kline_adj_factor_by_date": "kline_adj_factor_by_date_sources",
    "kline_stk_limit": "kline_stk_limit_sources",
    "kline_stk_limit_by_date": "kline_stk_limit_by_date_sources",
    "financial_report_income": "report_income_sources",
    "financial_report_balance": "report_balance_sources",
    "financial_report_cashflow": "report_cashflow_sources",
    "financial_report_indicator": "report_indicator_sources",
    "stock_list": "stock_list_sources",
}

# 各 data_key 已注册的数据源
_REGISTERED_SOURCES: dict[str, frozenset[str]] = {
    "kline_daily": frozenset({"tushare", "tdx_quant"}),
    "kline_daily_by_date": frozenset({"tushare", "tdx_quant"}),
    "kline_adj_factor": frozenset({"tushare"}),
    "kline_adj_factor_by_date": frozenset({"tushare"}),
    "kline_stk_limit": frozenset({"tushare"}),
    "kline_stk_limit_by_date": frozenset({"tushare"}),
    "financial_report_income": frozenset({"tushare"}),
    "financial_report_balance": frozenset({"tushare"}),
    "financial_report_cashflow": frozenset({"tushare"}),
    "financial_report_indicator": frozenset({"tushare"}),
    "stock_list": frozenset({"tushare"}),
}

DEFAULT_SOURCE_CONFIG: list[tuple[str, str, int]] = [
    ("kline_daily", "tdx_quant", 1),
    ("kline_daily", "tushare", 2),
    ("kline_daily_by_date", "tushare", 1),
    ("kline_daily_by_date", "tdx_quant", 2),
    ("kline_adj_factor", "tushare", 1),
    ("kline_adj_factor_by_date", "tushare", 1),
    ("kline_stk_limit", "tushare", 1),
    ("kline_stk_limit_by_date", "tushare", 1),
    ("financial_report_income", "tushare", 1),
    ("financial_report_balance", "tushare", 1),
    ("financial_report_cashflow", "tushare", 1),
    ("financial_report_indicator", "tushare", 1),
    ("stock_list", "tushare", 1),
]


def _parse_sources(raw: str) -> list[str]:
    return [s.strip().lower() for s in raw.split(",") if s.strip()]


class DataSourceConfigService:
    def __init__(self) -> None:
        self.db = Database()

    def get_source_chain(
        self,
        data_key: str,
        *,
        allowed_sources: Iterable[str] | None = None,
    ) -> list[str]:
        """
        返回 data_key 对应的数据源链（按优先级排序）。

        1. 查 DB enabled=True 记录
        2. 表为空或无匹配 → 读 settings 兜底
        3. 过滤未注册或不在 allowed_sources 中的源
        """
        key = data_key.strip()
        registered = _REGISTERED_SOURCES.get(key, frozenset())
        allowed = frozenset(s.lower() for s in allowed_sources) if allowed_sources else registered

        chain = self._load_from_db(key)
        if not chain:
            chain = self._load_from_settings(key)

        result: list[str] = []
        seen: set[str] = set()
        for source in chain:
            src = source.lower()
            if src not in registered or src not in allowed:
                continue
            if src in seen:
                continue
            seen.add(src)
            result.append(src)
        return result

    def sync_priorities_from_settings(self, data_key: str) -> int:
        """按 .env 中逗号顺序写入 DB priority（前者 priority=1），使配置变更即时生效。"""
        field = _SETTINGS_FALLBACK.get(data_key)
        if not field:
            return 0

        registered = _REGISTERED_SOURCES.get(data_key, frozenset())
        sources = [
            s for s in _parse_sources(getattr(settings, field, ""))
            if s in registered
        ]
        if not sources:
            return 0

        session: Session = self.db.get_session()
        updated = 0
        try:
            for priority, source in enumerate(sources, start=1):
                row = (
                    session.query(DataSourceConfigEntities)
                    .filter_by(data_key=data_key, source=source)
                    .first()
                )
                if row is None:
                    session.add(
                        DataSourceConfigEntities(
                            data_key=data_key,
                            source=source,
                            priority=priority,
                            enabled=True,
                        )
                    )
                    updated += 1
                elif row.priority != priority or not row.enabled:
                    row.priority = priority
                    row.enabled = True
                    updated += 1
            if updated:
                session.commit()
            return updated
        except (ProgrammingError, OperationalError):
            session.rollback()
            return 0
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def sync_default_priorities(self) -> int:
        """将已有配置行的 priority 校正为 DEFAULT_SOURCE_CONFIG（修正误配顺序）。"""
        session: Session = self.db.get_session()
        updated = 0
        try:
            for data_key, source, priority in DEFAULT_SOURCE_CONFIG:
                row = (
                    session.query(DataSourceConfigEntities)
                    .filter_by(data_key=data_key, source=source)
                    .first()
                )
                if row is not None and row.priority != priority:
                    row.priority = priority
                    updated += 1
            if updated:
                session.commit()
            return updated
        except (ProgrammingError, OperationalError):
            session.rollback()
            return 0
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def seed_missing_defaults(self) -> int:
        """补全缺失的默认配置行（已有表时 upsert 缺失的 data_key+source）。"""
        session: Session = self.db.get_session()
        added = 0
        try:
            existing = {
                (r.data_key, r.source)
                for r in session.query(
                    DataSourceConfigEntities.data_key,
                    DataSourceConfigEntities.source,
                ).all()
            }
            for data_key, source, priority in DEFAULT_SOURCE_CONFIG:
                if (data_key, source) in existing:
                    continue
                session.add(
                    DataSourceConfigEntities(
                        data_key=data_key,
                        source=source,
                        priority=priority,
                        enabled=True,
                    )
                )
                added += 1
            if added:
                session.commit()
            return added
        except (ProgrammingError, OperationalError):
            session.rollback()
            return 0
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def seed_defaults_if_empty(self) -> int:
        """表为空时写入默认优先级配置，返回写入行数。"""
        session: Session = self.db.get_session()
        try:
            count = session.query(DataSourceConfigEntities).count()
            if count > 0:
                return 0

            for data_key, source, priority in DEFAULT_SOURCE_CONFIG:
                session.add(
                    DataSourceConfigEntities(
                        data_key=data_key,
                        source=source,
                        priority=priority,
                        enabled=True,
                    )
                )
            session.commit()
            return len(DEFAULT_SOURCE_CONFIG)
        except (ProgrammingError, OperationalError):
            session.rollback()
            return 0
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _load_from_db(self, data_key: str) -> list[str]:
        session: Session = self.db.get_session()
        try:
            rows = (
                session.query(DataSourceConfigEntities)
                .filter(
                    DataSourceConfigEntities.data_key == data_key,
                    DataSourceConfigEntities.enabled.is_(True),
                )
                .order_by(DataSourceConfigEntities.priority.asc())
                .all()
            )
            return [r.source for r in rows]
        except (ProgrammingError, OperationalError):
            session.rollback()
            return []
        finally:
            session.close()

    def _load_from_settings(self, data_key: str) -> list[str]:
        field = _SETTINGS_FALLBACK.get(data_key)
        if not field:
            return []
        raw = getattr(settings, field, "")
        return _parse_sources(raw)
