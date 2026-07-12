"""财报披露计划（Tushare disclosure_date）。"""

from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class DisclosureDateEntities(Base):
    __tablename__ = "financial_disclosure_date"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), comment="TS 代码")
    ann_date = Column(String(8), comment="最新披露公告日")
    end_date = Column(String(8), comment="报告期")
    pre_date = Column(String(8), comment="预计披露日期")
    actual_date = Column(String(8), comment="实际披露日期")
    modify_date = Column(String(8), comment="披露日期修正记录")

    __table_args__ = (
        Index("idx_disclosure_date_end_date", "end_date"),
        Index("idx_disclosure_date_ts_code", "ts_code"),
        Index("idx_disclosure_date_unique", "ts_code", "end_date", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(DisclosureDateEntities)
