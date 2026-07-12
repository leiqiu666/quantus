"""股东户数 entities"""

from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class StkHoldernumberEntities(Base):
    __tablename__ = "financial_stock_holder"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    ts_code = Column(String(20), comment="股票代码")
    ann_date = Column(String(8), comment="公告日期")
    end_date = Column(String(8), comment="截止日期")
    holder_num = Column(Integer, comment="股东户数")

    __table_args__ = (
        Index('idx_stk_holdernumber_end_date', 'end_date'),
        Index('idx_stk_holdernumber_unique', 'ts_code', 'end_date', unique=True),
    )

if __name__ == "__main__":
    from src.common.database import sync_table
    sync_table(StkHoldernumberEntities)
