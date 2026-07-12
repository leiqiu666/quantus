"""Report indicator entities — tushare fina_indicator / fina_indicator_vip"""

from sqlalchemy import Column, Integer, String, Float, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ReportIndicatorEntities(Base):
    __tablename__ = "financial_report_indicator"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    ts_code = Column(String(20), comment="股票代码")
    ann_date = Column(String(8), comment="公告日期")
    end_date = Column(String(8), comment="报告期")
    update_flag = Column(String(1), comment="更新标识")

    # 每股指标
    eps = Column(Float, comment="基本每股收益")
    dt_eps = Column(Float, comment="稀释每股收益")
    bps = Column(Float, comment="每股净资产")
    ocfps = Column(Float, comment="每股经营活动产生的现金流量净额")
    cfps = Column(Float, comment="每股现金流量净额")

    # 盈利能力
    roe = Column(Float, comment="净资产收益率")
    roe_dt = Column(Float, comment="净资产收益率(扣除非经常性损益)")
    roa = Column(Float, comment="总资产报酬率")
    grossprofit_margin = Column(Float, comment="销售毛利率")
    netprofit_margin = Column(Float, comment="销售净利率")

    # 偿债能力
    current_ratio = Column(Float, comment="流动比率")
    quick_ratio = Column(Float, comment="速动比率")
    debt_to_assets = Column(Float, comment="资产负债率")

    # 营运能力
    ar_turn = Column(Float, comment="应收账款周转率(次)")
    assets_turn = Column(Float, comment="总资产周转率(次)")

    # 成长能力
    op_yoy = Column(Float, comment="营业利润同比增长率(%)")
    dt_netprofit_yoy = Column(Float, comment="归属母公司股东的净利润同比增长率(%)")
    tr_yoy = Column(Float, comment="营业总收入同比(%)")
    roe_yoy = Column(Float, comment="净资产收益率同比增长率(%)")
    equity_yoy = Column(Float, comment="净资产同比增长率")

    indicator_table = Column(JSONB, comment="财务指标详情（其余指标字段）")

    __table_args__ = (
        Index('idx_report_indicator_ts_code', 'ts_code'),
        Index('idx_report_indicator_end_date', 'end_date'),
        Index('idx_report_indicator_eps', 'eps'),
        Index('idx_report_indicator_roe', 'roe'),
        Index('idx_report_indicator_roa', 'roa'),
        Index('idx_report_indicator_debt_to_assets', 'debt_to_assets'),
        Index('idx_report_indicator_grossprofit_margin', 'grossprofit_margin'),
        Index('idx_report_indicator_netprofit_margin', 'netprofit_margin'),
        Index('idx_report_indicator_dt_netprofit_yoy', 'dt_netprofit_yoy'),
        Index(
            'idx_report_indicator_upsert_key',
            'ts_code', 'end_date', 'ann_date', 'update_flag',
            unique=True,
        ),
    )


if __name__ == "__main__":
    from src.common.database import sync_table
    sync_table(ReportIndicatorEntities, interactive=True)
