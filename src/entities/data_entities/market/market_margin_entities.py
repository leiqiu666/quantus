"""融资融券明细 entities"""

from sqlalchemy import Column, Integer, String, Float, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class MarginDetailEntities(Base):
    __tablename__ = "market_margin_detail"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    trade_date = Column(String(8), comment="交易日期")
    ts_code = Column(String(20), comment="股票代码")
    rzye = Column(Float, comment="融资余额(元)")
    rzmre = Column(Float, comment="融资买入额(元)")
    rzche = Column(Float, comment="融资偿还额(元)")
    rzrqye = Column(Float, comment="融资融券余额(元)")
    rqye = Column(Float, comment="融券余额(元)")
    rqyl = Column(Float, comment="融券余量(股)")
    rqmcl = Column(Float, comment="融券卖出量(股)")
    rqchl = Column(Float, comment="融券偿还量(股)")

    __table_args__ = (
        Index('idx_margin_detail_trade_date', 'trade_date'),
        Index('idx_margin_detail_unique', 'ts_code', 'trade_date', unique=True),
    )

if __name__ == "__main__":
    from src.common.database import sync_table
    sync_table(MarginDetailEntities)
