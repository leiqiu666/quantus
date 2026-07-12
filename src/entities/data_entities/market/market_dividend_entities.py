"""分红送股 entities"""

from sqlalchemy import Column, Integer, String, Float, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class DividendEntities(Base):
    __tablename__ = "market_dividend"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    ts_code = Column(String(20), comment="股票代码")
    end_date = Column(String(8), comment="分红年度")
    ann_date = Column(String(8), comment="预案公告日")
    div_proc = Column(String(20), comment="实施进度(预案/实施)")
    stk_div = Column(Float, comment="每股送转")
    stk_bo_rate = Column(Float, comment="每股送股比例")
    stk_co_rate = Column(Float, comment="每股转增比例")
    cash_div = Column(Float, comment="每股分红(税后)")
    cash_div_tax = Column(Float, comment="每股分红(税前)")
    record_date = Column(String(8), comment="股权登记日")
    ex_date = Column(String(8), comment="除权除息日")
    pay_date = Column(String(8), comment="派息日")
    div_listdate = Column(String(8), comment="红股上市日")
    imp_ann_date = Column(String(8), comment="实施公告日")
    base_date = Column(String(8), comment="基准日")
    base_share = Column(Float, comment="基准股本(万)")

    __table_args__ = (
        Index('idx_dividend_ts_code', 'ts_code'),
        Index('idx_dividend_ex_date', 'ex_date'),
        Index('idx_dividend_unique', 'ts_code', 'end_date', 'div_proc', unique=True),
    )

if __name__ == "__main__":
    from src.common.database import sync_table
    sync_table(DividendEntities)
