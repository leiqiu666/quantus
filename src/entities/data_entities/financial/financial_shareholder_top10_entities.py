"""前十大股东（Tushare top10_holders）。"""

from sqlalchemy import Column, Integer, Float, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Top10HoldersEntities(Base):
    __tablename__ = "financial_shareholder_top10"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), comment="TS 代码")
    ann_date = Column(String(8), comment="公告日期")
    end_date = Column(String(8), comment="报告期")
    holder_name = Column(String(200), comment="股东名称")
    hold_amount = Column(Float, comment="持有数量（股）")
    hold_ratio = Column(Float, comment="占总股本比例(%)")
    hold_float_ratio = Column(Float, comment="占流通股本比例(%)")
    hold_change = Column(Float, comment="持股变动")
    holder_type = Column(String(40), comment="股东类型")

    __table_args__ = (
        Index("idx_top10_holders_end_date", "end_date"),
        Index("idx_top10_holders_ts_code", "ts_code"),
        Index("idx_top10_holders_unique", "ts_code", "end_date", "holder_name", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(Top10HoldersEntities)
