"""通用完整性快照实体：记录每个数据源每个日/期的实到 vs 应到行数。"""

from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class CompletenessSnapshotEntities(Base):
    __tablename__ = "completeness_snapshot"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    source_name = Column(String(50), comment="数据源标识 (e.g. daily_basic, forecast)")
    date_key = Column(String(8), comment="日期键 (YYYYMMDD)")
    period_stock_count = Column(Integer, comment="该日/期应有行数 (在市股票数)")
    resolved_count = Column(Integer, comment="该日/期实到行数")

    __table_args__ = (
        Index(
            "idx_completeness_snapshot_source_date",
            "source_name",
            "date_key",
            unique=True,
        ),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(CompletenessSnapshotEntities)
