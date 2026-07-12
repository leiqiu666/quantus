"""沪深港通资金流向 entities"""

from sqlalchemy import Column, Integer, String, Float, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class MoneyflowHsgtEntities(Base):
    __tablename__ = "market_moneyflow_hsgt"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    trade_date = Column(String(8), comment="交易日期")
    ggt_ss = Column(Float, comment="港股通（上海）百万元")
    ggt_sz = Column(Float, comment="港股通（深圳）百万元")
    hgt = Column(Float, comment="沪股通（百万元）")
    sgt = Column(Float, comment="深股通（百万元）")
    north_money = Column(Float, comment="北向资金（百万元）")
    south_money = Column(Float, comment="南向资金（百万元）")

    __table_args__ = (
        Index("idx_moneyflow_hsgt_trade_date", "trade_date"),
        Index("idx_moneyflow_hsgt_unique", "trade_date", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(MoneyflowHsgtEntities)
