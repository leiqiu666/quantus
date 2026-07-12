"""Report income entities"""

from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, create_engine, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from datetime import datetime
from src.common.setting import settings

# create base class (模块级别，可被其他模块导入使用)
Base = declarative_base()

class ReportIncomeEntities(Base):
    __tablename__ = "financial_report_income"
    id = Column(Integer, primary_key=True,autoincrement=True,comment="ID")
    # stock basic information
    ts_code = Column(String(20),comment="股票代码")
    ann_date = Column(String(8),comment="公告日期")
    f_ann_date = Column(String(8),comment="实际公告日期")
    end_date = Column(String(8),comment= "报告期")
    report_type = Column(String(20),comment="报告期类型(1合并报表/2单季合并/3调整单季/4调整合并/5调整前合并/6母公司报表/7母公司单季报表/8母公司调整单季/9母公司调整/10母公司调整前/11母公司调整前合并/12母公司调整前)")
    comp_type = Column(String(5),comment="公司类型(1一般工商业/2银行/3保险/4证券)")
    end_type = Column(String(5),comment="报告期类型")

    # report income core data
    # operating total revenue
    total_revenue = Column(Float,comment="经营总收入")
    # operating total cost
    total_cogs = Column(Float,comment="营业总成本")
    oper_cost = Column(Float,comment="营业成本")
    rd_exp = Column(Float,comment="研发费用")
    sell_exp = Column(Float,comment="销售费用")
    admin_exp = Column(Float,comment="管理费用")
    biz_tax_surcharge = Column(Float,comment="营业税金及附加")
    fin_exp = Column(Float,comment="财务费用")
    fin_exp_int_exp = Column(Float,comment="利息费用")
    fin_exp_int_inc = Column(Float,comment="利息收入")
    # operating profit
    operate_profit = Column(Float,comment="营业利润")
    non_oper_income = Column(Float,comment="非营业总收入")
    non_oper_exp = Column(Float,comment="非营业总支出")
    # total profit
    total_profit = Column(Float,comment="利润总额")
    income_tax = Column(Float,comment="所得税")

    n_income = Column(Float,comment="净利润")
    continued_profit = Column(Float,comment="连续净利润")

    oth_compr_income = Column(Float,comment="其他综合收益")
    t_compr_income = Column(Float,comment="综合收益总额")
    compr_inc_attr_p = Column(Float,comment="归属于母公司(或股东)的综合收益总额")
    compr_inc_attr_m_s = Column(Float,comment="归属于少数股东的综合收益总额")

    update_flag = Column(String(1),comment="更新标志(1未更新/2已更新)")
    income_table = Column(JSONB,comment="利润表详情")

    # 为 ts_code、end_date、end_type、report_type、update_flag、total_revenue、total_cogs、operate_profit、total_profit、n_income 分别增加索引
    # 使用 __table_args__ 定义索引
    # 注意：PostgreSQL 索引名是数据库全局唯一的，需加表名前缀
    __table_args__ = (
        Index('idx_report_income_ts_code', 'ts_code'),
        Index('idx_report_income_end_date', 'end_date'),
        Index('idx_report_income_end_type', 'end_type'),
        Index('idx_report_income_report_type', 'report_type'),
        Index('idx_report_income_update_flag', 'update_flag'),
        Index('idx_report_income_total_revenue', 'total_revenue'),
        Index('idx_report_income_total_cogs', 'total_cogs'),
        Index('idx_report_income_rd_exp', 'rd_exp'),
        Index('idx_report_income_operate_profit', 'operate_profit'),
        Index('idx_report_income_total_profit', 'total_profit'),
        Index('idx_report_income_n_income', 'n_income'),
        # 复合唯一索引：ts_code + end_date + report_type + update_flag（用于 upsert 冲突检测）
        # 同一股票同一报告期可能有多种报表类型（合并报表、单季合并等）
        Index('idx_report_income_upsert_key', 'ts_code', 'end_date', 'f_ann_date','report_type', 'update_flag', unique=True),
    )

# 解释 if __name__ == "__main__":
# - 当直接运行此脚本时：__name__ == "__main__"，会执行下面的代码
# - 当其他模块导入此模块时：__name__ == "src.model.data_model.report_income"，不会执行下面的代码
# - 因此，其他模块可以正常导入 ReportIncome 类，不会受到影响
if __name__ == "__main__":
    from src.common.database import sync_table
    
    # 使用通用函数同步表结构
    sync_table(ReportIncomeEntities, interactive=True)