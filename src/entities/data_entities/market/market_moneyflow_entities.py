"""个股资金流向 entities"""

from sqlalchemy import Column, Integer, String, Float, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class MoneyflowEntities(Base):
    __tablename__ = "market_moneyflow"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    ts_code = Column(String(20), comment="股票代码")
    trade_date = Column(String(8), comment="交易日期")
    buy_sm_vol = Column(Float, comment="小单买入量(手)")
    buy_sm_amount = Column(Float, comment="小单买入金额(万元)")
    sell_sm_vol = Column(Float, comment="小单卖出量(手)")
    sell_sm_amount = Column(Float, comment="小单卖出金额(万元)")
    buy_md_vol = Column(Float, comment="中单买入量(手)")
    buy_md_amount = Column(Float, comment="中单买入金额(万元)")
    sell_md_vol = Column(Float, comment="中单卖出量(手)")
    sell_md_amount = Column(Float, comment="中单卖出金额(万元)")
    buy_lg_vol = Column(Float, comment="大单买入量(手)")
    buy_lg_amount = Column(Float, comment="大单买入金额(万元)")
    sell_lg_vol = Column(Float, comment="大单卖出量(手)")
    sell_lg_amount = Column(Float, comment="大单卖出金额(万元)")
    buy_elg_vol = Column(Float, comment="特大单买入量(手)")
    buy_elg_amount = Column(Float, comment="特大单买入金额(万元)")
    sell_elg_vol = Column(Float, comment="特大单卖出量(手)")
    sell_elg_amount = Column(Float, comment="特大单卖出金额(万元)")
    net_mf_vol = Column(Float, comment="净流入量(手)")
    net_mf_amount = Column(Float, comment="净流入金额(万元)")

    __table_args__ = (
        Index('idx_moneyflow_trade_date', 'trade_date'),
        Index('idx_moneyflow_unique', 'ts_code', 'trade_date', unique=True),
    )

if __name__ == "__main__":
    from src.common.database import sync_table
    sync_table(MoneyflowEntities)
