"""Report balance entities"""

from sqlalchemy import Column, Integer, String, DateTime, Float, JSON, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from src.common.setting import settings

Base = declarative_base()

class ReportBalanceEntities(Base):
    __tablename__ = "financial_report_balance"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    # stock basic information
    ts_code = Column(String(20),comment="股票代码")
    ann_date = Column(String(8),comment="公告日期")
    f_ann_date = Column(String(8),comment="实际公告日期")
    end_date = Column(String(8),comment= "报告期")
    report_type = Column(String(20),comment="报告期类型(1合并报表/2单季合并/3调整单季/4调整合并/5调整前合并/6母公司报表/7母公司单季报表/8母公司调整单季/9母公司调整/10母公司调整前/11母公司调整前合并/12母公司调整前)")
    comp_type = Column(String(5),comment="公司类型(1一般工商业/2银行/3保险/4证券)")
    end_type = Column(String(5),comment="报告期类型")
    # flow assets
    money_cap = Column(Float, comment="货币资金")
    trad_asset = Column(Float, comment="交易性金融资产")
    accounts_receiv_bill = Column(Float, comment="应收票据及应收款")
    notes_receiv = Column(Float, comment="应收票据")
    accounts_receiv = Column(Float, comment="应收账款")
    receiv_financing = Column(Float, comment=" 应收款项融资")
    oth_rcv_total = Column(Float, comment="其他应收款合计")
    inventories = Column(Float, comment="存货")
    contract_assets = Column(Float, comment="合同资产")
    oth_cur_assets = Column(Float, comment="其他流动资产")
    total_cur_assets = Column(Float, comment="流动资产合计")
    # non-current assets
    lt_eqt_invest = Column(Float, comment="长期股权投资")
    invest_real_estate = Column(Float, comment="投资性房地产")
    fix_assets = Column(Float, comment="固定资产")
    cip = Column(Float, comment="在建工程")
    use_right_assets = Column(Float, comment="使用权资产")
    intan_assets = Column(Float, comment="无形资产")
    amor_exp = Column(Float, comment="长期待摊费用")
    defer_tax_assets = Column(Float, comment="递延所得税资产")
    oth_nca = Column(Float, comment="其他非流动资产")
    total_nca = Column(Float, comment="非流动资产合计")
    total_assets = Column(Float, comment="资产合计")
    # non-current liabilities
    lt_borr = Column(Float, comment="长期借款")
    bond_payable = Column(Float, comment="应付债券")
    lease_liab = Column(Float, comment="租赁负债")
    deferred_inc = Column(Float, comment="递延收益")
    total_ncl = Column(Float, comment="非流动负债合计")
    total_liab = Column(Float, comment="负债合计")
    st_borr = Column(Float, comment="短期借款")
    # owner's equity
    total_share = Column(Float, comment="期末总股本")
    oth_eqt_tools = Column(Float, comment="其他权益工具")
    cap_rese = Column(Float, comment="资本公积")
    surplus_rese = Column(Float, comment="盈余公积")
    undistr_porfit = Column(Float, comment="未分配利润")
    treasury_share = Column(Float, comment="减:库存股")
    total_hldr_eqy_exc_min_int = Column(Float, comment="归属母公司股东权益合计")
    minority_int = Column(Float, comment="少数股东权益")
    total_hldr_eqy_inc_min_int = Column(Float, comment="股东权益合计")
    total_liab_hldr_eqy = Column(Float, comment="负债和股东权益合计")

    update_flag = Column(String(1),comment="更新标志(1未更新/2已更新)")
    balance_table = Column(JSONB,comment="资产负债表详情")

    __table_args__ = (
        Index('idx_report_balance_ts_code', 'ts_code'),
        Index('idx_report_balance_end_date', 'end_date'),
        Index('idx_report_balance_end_type', 'end_type'),
        Index('idx_report_balance_report_type', 'report_type'),
        Index('idx_report_balance_update_flag', 'update_flag'),
        Index('idx_report_balance_money_cap', 'money_cap'),
        Index('idx_report_balance_lt_eqt_invest', 'lt_eqt_invest'),
        Index('idx_report_balance_fix_assets', 'fix_assets'),
        Index('idx_report_balance_bond_payable', 'bond_payable'),
        Index('idx_report_balance_lt_borr', 'lt_borr'),
        Index('idx_report_balance_total_hldr_eqy_inc_min_int', 'total_hldr_eqy_inc_min_int'),
        Index('idx_report_balance_total_hldr_eqy_exc_min_int', 'total_hldr_eqy_exc_min_int'),
        Index('idx_report_balance_undistr_porfit', 'undistr_porfit'),
        Index('idx_report_balance_total_share', 'total_share'),
        # 复合唯一索引：ts_code + end_date + report_type + update_flag（用于 upsert 冲突检测）
        # 同一股票同一报告期可能有多种报表类型（合并报表、单季合并等）
        Index('idx_report_balance_upsert_key', 'ts_code', 'end_date', 'f_ann_date','report_type', 'update_flag', unique=True),
    )


if __name__ == "__main__":
    from src.common.database import sync_table
    
    # 使用通用函数同步表结构
    sync_table(ReportBalanceEntities, interactive=True)







