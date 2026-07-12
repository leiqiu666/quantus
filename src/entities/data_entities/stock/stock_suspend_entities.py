"""停复牌 entities"""

from sqlalchemy import Column, Integer, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class SuspendEntities(Base):
    __tablename__ = "stock_suspend"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    ts_code = Column(String(20), comment="股票代码")
    trade_date = Column(String(8), comment="停复牌日期")
    suspend_timing = Column(String(2), comment="停牌时间（S：半天/全天，R：上午/下午/全天）")
    suspend_type = Column(String(2), comment="停复牌类型（S：停牌，R：复牌）")

    __table_args__ = (
        Index('idx_suspend_trade_date', 'trade_date'),
        Index('idx_suspend_unique', 'ts_code', 'trade_date', 'suspend_type', 'suspend_timing', unique=True),
    )

if __name__ == "__main__":
    from src.common.database import sync_table
    sync_table(SuspendEntities)
