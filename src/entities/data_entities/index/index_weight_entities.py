"""指数成分权重 entities"""

from sqlalchemy import Column, Integer, String, Float, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class IndexWeightEntities(Base):
    __tablename__ = "index_weight"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    index_code = Column(String(20), comment="指数代码")
    con_code = Column(String(20), comment="成分代码")
    trade_date = Column(String(8), comment="交易日期")
    weight = Column(Float, comment="权重")

    __table_args__ = (
        Index('idx_index_weight_trade_date', 'trade_date'),
        Index('idx_index_weight_con_code', 'con_code'),
        Index('idx_index_weight_unique', 'index_code', 'con_code', 'trade_date', unique=True),
    )

if __name__ == "__main__":
    from src.common.database import sync_table
    sync_table(IndexWeightEntities)
