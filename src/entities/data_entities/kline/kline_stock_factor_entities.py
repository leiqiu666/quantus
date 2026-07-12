"""技术面因子 entities"""

from sqlalchemy import Column, Integer, String, Float, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class StkFactorEntities(Base):
    __tablename__ = "kline_stock_factor"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    ts_code = Column(String(20), comment="股票代码")
    trade_date = Column(String(8), comment="交易日期")
    macd_dif = Column(Float, comment="MACD DIF")
    macd_dea = Column(Float, comment="MACD DEA")
    macd = Column(Float, comment="MACD 柱")
    kdj_k = Column(Float, comment="KDJ K 值")
    kdj_d = Column(Float, comment="KDJ D 值")
    kdj_j = Column(Float, comment="KDJ J 值")
    rsi_6 = Column(Float, comment="RSI 6日")
    rsi_12 = Column(Float, comment="RSI 12日")
    rsi_24 = Column(Float, comment="RSI 24日")
    boll_upper = Column(Float, comment="BOLL 上轨")
    boll_mid = Column(Float, comment="BOLL 中轨")
    boll_lower = Column(Float, comment="BOLL 下轨")
    cci = Column(Float, comment="CCI")

    __table_args__ = (
        Index('idx_stk_factor_trade_date', 'trade_date'),
        Index('idx_stk_factor_unique', 'ts_code', 'trade_date', unique=True),
    )

if __name__ == "__main__":
    from src.common.database import sync_table
    sync_table(StkFactorEntities)
