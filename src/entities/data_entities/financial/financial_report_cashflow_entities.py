"""Report cashflow entities"""

from sqlalchemy import Column, Integer, String, Float, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ReportCashflowEntities(Base):
    __tablename__ = "financial_report_cashflow"
    id = Column(Integer, primary_key=True, autoincrement=True, comment="ID")
    # stock basic information
    ts_code = Column(String(20),comment="股票代码")
    ann_date = Column(String(8),comment="公告日期")
    f_ann_date = Column(String(8),comment="实际公告日期")
    end_date = Column(String(8),comment= "报告期")
    report_type = Column(String(20),comment="报告期类型(1合并报表/2单季合并/3调整单季/4调整合并/5调整前合并/6母公司报表/7母公司单季报表/8母公司调整单季/9母公司调整/10母公司调整前/11母公司调整前合并/12母公司调整前)")
    comp_type = Column(String(5),comment="公司类型(1一般工商业/2银行/3保险/4证券)")
    end_type = Column(String(5),comment="报告期类型")
    # cash flow generate from operating activities
    c_fr_sale_sg = Column(Float,comment="销售商品、提供劳务收到的现金")
    n_depos_incr_fi = Column(Float,comment="客户存款和同业存放款项净增加额")
    ifc_cash_incr = Column(Float,comment="收取利息和手续费净增加额")
    c_fr_oth_operate_a = Column(Float,comment="收到其他与经营活动有关的现金")
    c_inf_fr_operate_a = Column(Float,comment="经营活动现金流入小计")
    c_paid_goods_s = Column(Float,comment="购买商品、接受劳务支付的现金")
    n_incr_clt_loan_adv = Column(Float,comment="客户贷款及垫款净增加额")
    n_incr_dep_cbob = Column(Float,comment="存放中央银行和同业款项净增加额")
    pay_handling_chrg = Column(Float,comment="支付手续费净增加额")
    c_paid_to_for_empl = Column(Float,comment="支付给职工以及为职工支付的现金")
    c_paid_for_taxes = Column(Float,comment="支付的各项税费")
    oth_cash_pay_oper_act = Column(Float,comment="支付其他与经营活动有关的现金")
    
    st_cash_out_act = Column(Float,comment="经营活动现金流出小计")
    n_cashflow_act = Column(Float,comment="经营活动产生的现金流量净额")
    # cash flow generate from investing activities
    c_disp_withdrwl_invest = Column(Float,comment="收回投资收到的现金")
    c_recp_return_invest = Column(Float,comment="取得投资收益收到的现金")
    n_recp_disp_fiolta = Column(Float,comment="处置固定资产、无形资产和其他长期资产收回的现金净额")
    oth_recp_ral_inv_act = Column(Float,comment="收到其他与投资活动有关的现金")
    stot_inflows_inv_act = Column(Float,comment="投资活动现金流入小计")
    c_pay_acq_const_fiolta = Column(Float,comment="购建固定资产、无形资产和其他长期资产支付的现金")
    c_paid_invest = Column(Float,comment="投资支付的现金")
    oth_pay_ral_inv_act = Column(Float,comment="支付其他与投资活动有关的现金")
    stot_out_inv_act = Column(Float,comment="投资活动现金流出小计")
    n_cashflow_inv_act = Column(Float,comment="投资活动产生的现金流量净额")
    # cash flow generate from financing activities
    stot_cash_in_fnc_act = Column(Float,comment="筹资活动现金流入小计")
    c_pay_dist_dpcp_int_exp = Column(Float,comment="分配股利、利润或偿付利息支付的现金")
    incl_dvd_profit_paid_sc_ms = Column(Float,comment="其中:子公司支付给少数股东的股利、利润")
    oth_cashpay_ral_fnc_act = Column(Float,comment="支付其他与筹资活动有关的现金")
    stot_cashout_fnc_act = Column(Float,comment="筹资活动现金流出小计")
    n_cash_flows_fnc_act = Column(Float,comment="筹资活动产生的现金流量净额")
    eff_fx_flu_cash = Column(Float,comment="汇率变动对现金及现金等价物的影响")
    n_incr_cash_cash_equ = Column(Float,comment="现金及现金等价物净增加额")
    c_cash_equ_beg_period = Column(Float,comment="期初现金及现金等价物余额")
    c_cash_equ_end_period = Column(Float,comment="期末现金及现金等价物余额")

    update_flag = Column(String(1),comment="更新标志(1未更新/2已更新)")
    cashflow_table = Column(JSONB,comment="现金流量表详情")

    __table_args__ = (
        Index('idx_report_cashflow_ts_code', 'ts_code'),
        Index('idx_report_cashflow_end_date', 'end_date'),
        Index('idx_report_cashflow_end_type', 'end_type'),
        Index('idx_report_cashflow_report_type', 'report_type'),
        Index('idx_report_cashflow_update_flag', 'update_flag'),
        Index('idx_report_cashflow_c_fr_sale_sg', 'c_fr_sale_sg'),
        Index('idx_report_cashflow_n_depos_incr_fi', 'n_depos_incr_fi'),
        # 复合唯一索引：ts_code + end_date + report_type + update_flag（用于 upsert 冲突检测）
        # 同一股票同一报告期可能有多种报表类型（合并报表、单季合并等）
        Index('idx_report_cashflow_upsert_key', 'ts_code', 'end_date', 'f_ann_date','report_type', 'update_flag', unique=True), 

    )
    
if __name__ == "__main__":
    from src.common.database import sync_table
    
    # 使用通用函数同步表结构
    sync_table(ReportCashflowEntities, interactive=True)









