"""业绩快报（Tushare express_vip）。"""

from sqlalchemy import Column, Integer, Float, String, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ExpressEntities(Base):
    __tablename__ = "financial_express"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), comment="TS 代码")
    ann_date = Column(String(8), comment="公告日期")
    end_date = Column(String(8), comment="报告期")
    revenue = Column(Float, comment="营业收入（元）")
    operate_profit = Column(Float, comment="营业利润（元）")
    total_profit = Column(Float, comment="利润总额（元）")
    n_income = Column(Float, comment="净利润（元）")
    total_assets = Column(Float, comment="总资产（元）")
    total_hldr_eqy_exc_min_int = Column(Float, comment="股东权益（元）")
    diluted_eps = Column(Float, comment="每股收益（元）")
    diluted_roe = Column(Float, comment="净资产收益率（%）")
    yoy_net_profit = Column(Float, comment="去年同期净利润")
    bps = Column(Float, comment="每股净资产")
    yoy_sales = Column(Float, comment="营收同比(%)")
    yoy_op = Column(Float, comment="营业利润同比(%)")
    yoy_tp = Column(Float, comment="利润总额同比(%)")
    yoy_dedu_np = Column(Float, comment="归母净利同比(%)")
    yoy_eps = Column(Float, comment="EPS同比(%)")
    yoy_roe = Column(Float, comment="ROE同比增减")
    growth_assets = Column(Float, comment="总资产增长率")
    yoy_equity = Column(Float, comment="股东权益增长率")

    __table_args__ = (
        Index("idx_express_end_date", "end_date"),
        Index("idx_express_ts_code", "ts_code"),
        Index("idx_express_unique", "ts_code", "end_date", unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table

    sync_table(ExpressEntities)
