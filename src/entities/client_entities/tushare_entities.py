from typing import Dict, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Tushare income / income_vip 字段 -> report_income 实体字段
REPORT_INCOME_COLUMN_MAP: Dict[str, str] = {
    "ts_code": "ts_code",
    "ann_date": "ann_date",
    "f_ann_date": "f_ann_date",
    "end_date": "end_date",
    "report_type": "report_type",
    "comp_type": "comp_type",
    "end_type": "end_type",
    "total_revenue": "total_revenue",
    "total_cogs": "total_cogs",
    "oper_cost": "oper_cost",
    "rd_exp": "rd_exp",
    "sell_exp": "sell_exp",
    "admin_exp": "admin_exp",
    "biz_tax_surcharge": "biz_tax_surcharge",
    "fin_exp": "fin_exp",
    "fin_exp_int_exp": "fin_exp_int_exp",
    "fin_exp_int_inc": "fin_exp_int_inc",
    "operate_profit": "operate_profit",
    "non_oper_income": "non_oper_income",
    "non_oper_exp": "non_oper_exp",
    "total_profit": "total_profit",
    "income_tax": "income_tax",
    "n_income": "n_income",
    "continued_profit": "continued_profit",
    "oth_compr_income": "oth_compr_income",
    "t_compr_income": "t_compr_income",
    "compr_inc_attr_p": "compr_inc_attr_p",
    "compr_inc_attr_m_s": "compr_inc_attr_m_s",
    "update_flag": "update_flag",
    "income_table": "income_table",
}

# Tushare balancesheet / balancesheet_vip 字段 -> report_balance 实体字段
REPORT_BALANCE_COLUMN_MAP: Dict[str, str] = {
    "ts_code": "ts_code",
    "ann_date": "ann_date",
    "f_ann_date": "f_ann_date",
    "end_date": "end_date",
    "report_type": "report_type",
    "comp_type": "comp_type",
    "end_type": "end_type",
    "money_cap": "money_cap",
    "trad_asset": "trad_asset",
    "accounts_receiv_bill": "accounts_receiv_bill",
    "notes_receiv": "notes_receiv",
    "accounts_receiv": "accounts_receiv",
    "receiv_financing": "receiv_financing",
    "oth_rcv_total": "oth_rcv_total",
    "inventories": "inventories",
    "contract_assets": "contract_assets",
    "oth_cur_assets": "oth_cur_assets",
    "total_cur_assets": "total_cur_assets",
    "lt_eqt_invest": "lt_eqt_invest",
    "invest_real_estate": "invest_real_estate",
    "fix_assets": "fix_assets",
    "cip": "cip",
    "use_right_assets": "use_right_assets",
    "intan_assets": "intan_assets",
    "amor_exp": "amor_exp",
    "defer_tax_assets": "defer_tax_assets",
    "oth_nca": "oth_nca",
    "total_nca": "total_nca",
    "total_assets": "total_assets",
    "lt_borr": "lt_borr",
    "bond_payable": "bond_payable",
    "lease_liab": "lease_liab",
    "deferred_inc": "deferred_inc",
    "total_ncl": "total_ncl",
    "total_liab": "total_liab",
    "st_borr": "st_borr",
    "total_share": "total_share",
    "oth_eqt_tools": "oth_eqt_tools",
    "cap_rese": "cap_rese",
    "surplus_rese": "surplus_rese",
    "undistr_porfit": "undistr_porfit",
    "treasury_share": "treasury_share",
    "total_hldr_eqy_exc_min_int": "total_hldr_eqy_exc_min_int",
    "minority_int": "minority_int",
    "total_hldr_eqy_inc_min_int": "total_hldr_eqy_inc_min_int",
    "total_liab_hldr_eqy": "total_liab_hldr_eqy",
    "update_flag": "update_flag",
    "balance_table": "balance_table",
}

# Tushare cashflow / cashflow_vip 字段 -> report_cashflow 实体字段
REPORT_CASHFLOW_COLUMN_MAP: Dict[str, str] = {
    "ts_code": "ts_code",
    "ann_date": "ann_date",
    "f_ann_date": "f_ann_date",
    "end_date": "end_date",
    "report_type": "report_type",
    "comp_type": "comp_type",
    "end_type": "end_type",
    "c_fr_sale_sg": "c_fr_sale_sg",
    "n_depos_incr_fi": "n_depos_incr_fi",
    "ifc_cash_incr": "ifc_cash_incr",
    "c_fr_oth_operate_a": "c_fr_oth_operate_a",
    "c_inf_fr_operate_a": "c_inf_fr_operate_a",
    "c_paid_goods_s": "c_paid_goods_s",
    "n_incr_clt_loan_adv": "n_incr_clt_loan_adv",
    "n_incr_dep_cbob": "n_incr_dep_cbob",
    "pay_handling_chrg": "pay_handling_chrg",
    "c_paid_to_for_empl": "c_paid_to_for_empl",
    "c_paid_for_taxes": "c_paid_for_taxes",
    "oth_cash_pay_oper_act": "oth_cash_pay_oper_act",
    "st_cash_out_act": "st_cash_out_act",
    "n_cashflow_act": "n_cashflow_act",
    "c_disp_withdrwl_invest": "c_disp_withdrwl_invest",
    "c_recp_return_invest": "c_recp_return_invest",
    "n_recp_disp_fiolta": "n_recp_disp_fiolta",
    "oth_recp_ral_inv_act": "oth_recp_ral_inv_act",
    "stot_inflows_inv_act": "stot_inflows_inv_act",
    "c_pay_acq_const_fiolta": "c_pay_acq_const_fiolta",
    "c_paid_invest": "c_paid_invest",
    "oth_pay_ral_inv_act": "oth_pay_ral_inv_act",
    "stot_out_inv_act": "stot_out_inv_act",
    "n_cashflow_inv_act": "n_cashflow_inv_act",
    "stot_cash_in_fnc_act": "stot_cash_in_fnc_act",
    "c_pay_dist_dpcp_int_exp": "c_pay_dist_dpcp_int_exp",
    "incl_dvd_profit_paid_sc_ms": "incl_dvd_profit_paid_sc_ms",
    "oth_cashpay_ral_fnc_act": "oth_cashpay_ral_fnc_act",
    "stot_cashout_fnc_act": "stot_cashout_fnc_act",
    "n_cash_flows_fnc_act": "n_cash_flows_fnc_act",
    "eff_fx_flu_cash": "eff_fx_flu_cash",
    "n_incr_cash_cash_equ": "n_incr_cash_cash_equ",
    "c_cash_equ_beg_period": "c_cash_equ_beg_period",
    "c_cash_equ_end_period": "c_cash_equ_end_period",
    "update_flag": "update_flag",
    "cashflow_table": "cashflow_table",
}

# Tushare fina_indicator / fina_indicator_vip 字段 -> report_indicator 实体字段
REPORT_INDICATOR_COLUMN_MAP: Dict[str, str] = {
    "ts_code": "ts_code",
    "ann_date": "ann_date",
    "end_date": "end_date",
    "update_flag": "update_flag",
    # 每股指标
    "eps": "eps",
    "dt_eps": "dt_eps",
    "bps": "bps",
    "ocfps": "ocfps",
    "cfps": "cfps",
    # 盈利能力
    "roe": "roe",
    "roe_dt": "roe_dt",
    "roa": "roa",
    "grossprofit_margin": "grossprofit_margin",
    "netprofit_margin": "netprofit_margin",
    # 偿债能力
    "current_ratio": "current_ratio",
    "quick_ratio": "quick_ratio",
    "debt_to_assets": "debt_to_assets",
    # 营运能力
    "ar_turn": "ar_turn",
    "assets_turn": "assets_turn",
    # 成长能力
    "op_yoy": "op_yoy",
    "dt_netprofit_yoy": "dt_netprofit_yoy",
    "tr_yoy": "tr_yoy",
    "roe_yoy": "roe_yoy",
    "equity_yoy": "equity_yoy",
    # JSONB 兜底
    "indicator_table": "indicator_table",
}


class TushareEntities(BaseSettings):
    """
    使用 BaseSettings 管理各个 Tushare API 的字段配置。

    - 默认值写在代码里
    - 如需覆盖，可以在 .env 中设置环境变量（支持逗号分隔或 JSON 数组）
      例如：
        TUSHARE_STOCK_BASIC=ts_code,symbol,name
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="TUSHARE_",  # 所有字段都会加此前缀读取环境变量
    )

    # 例如：stock_basic 接口的字段
    stock_basic: List[str] = Field(
        default=[
            "ts_code",
            "symbol",
            "name",
            "area",
            "cnspell",
            "market",
            "list_date",
            "fullname",
            "enname",
            "curr_type",
            "list_status",
            "exchange",
            "delist_date",
            "is_hs",
        ],
        description="stock_basic 接口需要的字段列表",
    )

    daily: List[str] = Field(
        default=[
            "ts_code",
            "trade_date",
            "open",
            "high",
            "low",
            "close",
            "pre_close",
            "change",
            "pct_chg",
            "vol",
            "amount",
        ],
        description="daily 日线行情接口字段列表",
    )

    adj_factor: List[str] = Field(
        default=[
            "ts_code",
            "trade_date",
            "adj_factor",
        ],
        description="adj_factor 复权因子接口字段列表",
    )

    stk_limit: List[str] = Field(
        default=[
            "ts_code",
            "trade_date",
            "up_limit",
            "down_limit",
        ],
        description="stk_limit 涨跌停价格接口字段列表",
    )

    daily_basic: List[str] = Field(
        default=[
            "ts_code",
            "trade_date",
            "close",
            "turnover_rate",
            "turnover_rate_f",
            "volume_ratio",
            "pe",
            "pe_ttm",
            "pb",
            "ps",
            "ps_ttm",
            "dv_ratio",
            "dv_ttm",
            "total_share",
            "float_share",
            "free_share",
            "total_mv",
            "circ_mv",
        ],
        description="daily_basic 每日基本面指标接口字段列表",
    )

    stk_premarket: List[str] = Field(
        default=[
            "trade_date",
            "ts_code",
            "total_share",
            "float_share",
            "pre_close",
            "up_limit",
            "down_limit",
        ],
        description="stk_premarket 盘前股本接口字段列表",
    )

    share_float: List[str] = Field(
        default=[
            "ts_code",
            "ann_date",
            "float_date",
            "float_share",
            "float_ratio",
            "holder_name",
            "share_type",
        ],
        description="share_float 限售股解禁接口字段列表",
    )

    trade_cal: List[str] = Field(
        default=[
            "exchange",
            "cal_date",
            "is_open",
            "pretrade_date",
        ],
        description="trade_cal 交易日历接口字段列表",
    )

    suspend_d: List[str] = Field(
        default=[
            "ts_code",
            "trade_date",
            "suspend_timing",
            "suspend_type",
        ],
        description="suspend_d 每日停复牌信息接口字段列表",
    )

    @property
    def report_income_column_map(self) -> Dict[str, str]:
        """Tushare 利润表字段 -> report_income 实体字段。"""
        return REPORT_INCOME_COLUMN_MAP

    @property
    def report_balance_column_map(self) -> Dict[str, str]:
        """Tushare 资产负债表字段 -> report_balance 实体字段。"""
        return REPORT_BALANCE_COLUMN_MAP

    @property
    def report_cashflow_column_map(self) -> Dict[str, str]:
        """Tushare 现金流量表字段 -> report_cashflow 实体字段。"""
        return REPORT_CASHFLOW_COLUMN_MAP

    @property
    def report_indicator_column_map(self) -> Dict[str, str]:
        """Tushare 财务指标字段 -> report_indicator 实体字段。"""
        return REPORT_INDICATOR_COLUMN_MAP

    @field_validator("*", mode="before")
    @classmethod
    def split_str_to_list(cls, v):
        """
        支持两种覆盖方式：
        1. 逗号分隔字符串：ts_code,symbol,name
        2. JSON 数组：["ts_code","symbol","name"]
        """
        if isinstance(v, str):
            # 先尝试按 JSON 解析：如果是 JSON 字符串，交给 Pydantic 自己处理
            v_strip = v.strip()
            if v_strip.startswith("[") and v_strip.endswith("]"):
                return v
            # 否则认为是逗号分隔字符串
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


# stk_factor_pro 接口：我们请求的字段（无后缀 + _hfq 后复权）
# _bfq/_qfq 不请求；OHLCV 及 adj_factor 已在 kline_daily，也不请求
STK_FACTOR_PRO_FIELDS: List[str] = [
    "ts_code", "trade_date",
    # ── 无后缀：基本面 + 量价 + 统计 ──
    "turnover_rate", "turnover_rate_f", "volume_ratio",
    "pe", "pe_ttm", "pb", "ps", "ps_ttm",
    "dv_ratio", "dv_ttm",
    "total_share", "float_share", "free_share", "total_mv", "circ_mv",
    "downdays", "updays", "lowdays", "topdays",
    # ── _hfq 后复权技术指标 ──
    "asi_hfq", "asit_hfq", "atr_hfq", "bbi_hfq",
    "bias1_hfq", "bias2_hfq", "bias3_hfq",
    "boll_lower_hfq", "boll_mid_hfq", "boll_upper_hfq",
    "brar_ar_hfq", "brar_br_hfq",
    "cci_hfq", "cr_hfq",
    "dfma_dif_hfq", "dfma_difma_hfq",
    "dmi_adx_hfq", "dmi_adxr_hfq", "dmi_mdi_hfq", "dmi_pdi_hfq",
    "dpo_hfq", "madpo_hfq",
    "ema_hfq_5", "ema_hfq_10", "ema_hfq_20", "ema_hfq_30", "ema_hfq_60", "ema_hfq_90", "ema_hfq_250",
    "emv_hfq", "maemv_hfq",
    "expma_12_hfq", "expma_50_hfq",
    "kdj_hfq", "kdj_d_hfq", "kdj_k_hfq",
    "ktn_down_hfq", "ktn_mid_hfq", "ktn_upper_hfq",
    "ma_hfq_5", "ma_hfq_10", "ma_hfq_20", "ma_hfq_30", "ma_hfq_60", "ma_hfq_90", "ma_hfq_250",
    "macd_hfq", "macd_dea_hfq", "macd_dif_hfq",
    "mass_hfq", "ma_mass_hfq",
    "mfi_hfq",
    "mtm_hfq", "mtmma_hfq",
    "obv_hfq",
    "psy_hfq", "psyma_hfq",
    "roc_hfq", "maroc_hfq",
    "rsi_hfq_6", "rsi_hfq_12", "rsi_hfq_24",
    "taq_down_hfq", "taq_mid_hfq", "taq_up_hfq",
    "trix_hfq", "trma_hfq",
    "vr_hfq",
    "wr_hfq", "wr1_hfq",
    "xsii_td1_hfq", "xsii_td2_hfq", "xsii_td3_hfq", "xsii_td4_hfq",
]

# _hfq 后缀重命名 + 语义优化映射（tushare 原名 → 本地列名）
STK_FACTOR_PRO_RENAME: Dict[str, str] = {
    # 无后缀：仅优化 4 个
    "downdays": "down_streak",
    "updays": "up_streak",
    "lowdays": "low_period",
    "topdays": "high_period",
}
# 批量生成 _hfq 去后缀映射
for _f in STK_FACTOR_PRO_FIELDS:
    if _f.endswith("_hfq"):
        STK_FACTOR_PRO_RENAME[_f] = _f.removesuffix("_hfq")
    elif "_hfq_" in _f:
        STK_FACTOR_PRO_RENAME[_f] = _f.replace("_hfq_", "_")


# 对外暴露一个单例，方便直接引用
tushare_entities = TushareEntities()
