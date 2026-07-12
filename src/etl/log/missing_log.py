from datetime import datetime
from typing import Optional

from sqlalchemy import delete, tuple_
from sqlalchemy.dialects import postgresql

from src.common.database import Database
from src.entities.data_entities.log_missing import LogMissing


class MissingLog:
    def __init__(self):
        self.db = Database()

    def get_missing_log(
        self,
        ts_code: str,
        missing_entity: str,
        missing_date: str,
    ) -> Optional[LogMissing]:
        """按 ts_code + missing_entity + missing_date 查询单条缺失日志，不存在则 None。"""
        return self.db.get_one(
            LogMissing,
            ts_code=ts_code,
            missing_entity=missing_entity,
            missing_date=missing_date,
        )

    def upsert_missing_logs(
        self,
        missing_items: list[str],
        missing_entity: str = "report",
    ) -> int:
        """
        批量写入缺失日志：单次 INSERT ... ON CONFLICT DO UPDATE，
        try_count 由数据库原子自增（不存在=1，已存在=旧值+1），消除 N+1。

        Args:
            missing_items: 元素格式为 "ts_code,missing_date" 的列表
            missing_entity: 缺失实体类型，默认 report
        Returns:
            int: 处理的记录数（包含已存在的更新）
        """
        if not missing_items:
            return 0

        now = datetime.now()
        records: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for missing_item in missing_items:
            if "," not in missing_item:
                continue
            ts_code, missing_date = missing_item.split(",", 1)
            ts_code = ts_code.strip()
            missing_date = missing_date.strip()
            if not ts_code or not missing_date:
                continue
            key = (ts_code, missing_date)
            if key in seen:
                continue
            seen.add(key)
            records.append(
                {
                    "ts_code": ts_code,
                    "missing_entity": missing_entity,
                    "missing_date": missing_date,
                    "try_count": 1,
                    "last_try_time": now,
                }
            )
        if not records:
            return 0

        table = LogMissing.__table__
        insert_stmt = postgresql.insert(table)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["ts_code", "missing_entity", "missing_date"],
            set_={
                "try_count": LogMissing.try_count + 1,
                "last_try_time": insert_stmt.excluded.last_try_time,
            },
        )

        session = self.db.get_session()
        try:
            session.execute(upsert_stmt, records)
            session.commit()
            return len(records)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete_missing_logs(
        self,
        missing_items: list[str],
        missing_entity: str,
    ) -> int:
        """
        批量物理删除缺失登记（补拉成功后调用）。

        Args:
            missing_items: 元素格式为 "ts_code,missing_date" 的列表
            missing_entity: 缺失实体类型（必传）
        Returns:
            int: 实际删除行数；不存在的项静默跳过
        """
        if not missing_items:
            return 0

        pairs: set[tuple[str, str]] = set()
        for item in missing_items:
            if "," not in item:
                continue
            ts_code, missing_date = item.split(",", 1)
            ts_code = ts_code.strip()
            missing_date = missing_date.strip()
            if not ts_code or not missing_date:
                continue
            pairs.add((ts_code, missing_date))
        if not pairs:
            return 0

        table = LogMissing.__table__
        stmt = delete(table).where(
            table.c.missing_entity == missing_entity,
            tuple_(table.c.ts_code, table.c.missing_date).in_(list(pairs)),
        )

        session = self.db.get_session()
        try:
            result = session.execute(stmt)
            session.commit()
            return result.rowcount or 0
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_missing_log_by_ts_code(
        self,
        ts_code: str,
        missing_entity: Optional[str] = None,
    ) -> list[LogMissing]:
        """
        按股票查询其全部待补拉缺失项；missing_entity=None 时跨域返回。
        按 missing_date 升序，无记录返回 []。
        """
        session = self.db.get_session()
        try:
            query = session.query(LogMissing).filter(LogMissing.ts_code == ts_code)
            if missing_entity is not None:
                query = query.filter(LogMissing.missing_entity == missing_entity)
            return query.order_by(LogMissing.missing_date.asc()).all()
        finally:
            session.close()
