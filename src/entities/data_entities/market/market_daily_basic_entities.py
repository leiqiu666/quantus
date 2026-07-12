"""每日基本面指标 entities"""

from sqlalchemy import Column, Integer, String, Float, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class DailyBasicEntities(Base):
    __tablename__ = "market_daily_basic"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    ts_code = Column(String(20), comment="股票代码")
    trade_date = Column(String(8), comment="交易日期")
    close = Column(Float, comment="收盘价")
    turnover_rate = Column(Float, comment="换手率")
    turnover_rate_f = Column(Float, comment="换手率(自由流通)")
    volume_ratio = Column(Float, comment="量比")
    pe = Column(Float, comment="市盈率")
    pe_ttm = Column(Float, comment="市盈率TTM")
    pb = Column(Float, comment="市净率")
    ps = Column(Float, comment="市销率")
    ps_ttm = Column(Float, comment="市销率TTM")
    dv_ratio = Column(Float, comment="股息率")
    dv_ttm = Column(Float, comment="股息率TTM")
    total_share = Column(Float, comment="总股本(万股)")
    float_share = Column(Float, comment="流通股本(万股)")
    free_share = Column(Float, comment="自由流通股本(万)")
    total_mv = Column(Float, comment="总市值(万元)")
    circ_mv = Column(Float, comment="流通市值(万元)")

    __table_args__ = (
        Index('idx_daily_basic_trade_date', 'trade_date'),
        Index('idx_daily_basic_unique', 'ts_code', 'trade_date', unique=True),
    )

if __name__ == "__main__":
    from src.common.database import sync_table
    sync_table(DailyBasicEntities)
