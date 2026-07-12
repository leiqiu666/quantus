from __future__ import annotations

import pandas as pd
from typing import Type, Any, List

from src.common.function import missing_quarter_report_periods
from src.etl.extract.local.stock.stock_local_extract import StockExtract

class ReportTransform:
    def __init__(self):
         self.QUARTER_END_DATES = ("0331", "0630", "0930", "1231")
    # staticmethod 静态方法，不需要实例化就可以调用
    @staticmethod
    def report_transform_merge_now(report_income_df: pd.DataFrame) -> pd.DataFrame:
        """
        合并财报数据并清洗：对"同一维度多条记录"按优先级择优保留一条。

        三表（income/balance/cashflow）：将 report_type 统一映射为 "merge_now"。
        财务指标（fina_indicator）：无 report_type 列，按 (ts_code, end_date) 去重。

        清洗规则:
            - 同一组有多条时，优先保留 update_flag == '1'。
            - 若 update_flag == '1' 仍有多条，则保留公告日期最大的一条（f_ann_date 或 ann_date）。
        """
        if report_income_df is None or report_income_df.empty:
            return pd.DataFrame() if report_income_df is None else report_income_df.copy()

        has_report_type = "report_type" in report_income_df.columns
        has_f_ann_date = "f_ann_date" in report_income_df.columns

        required_cols = {"ts_code", "end_date", "update_flag"}
        if has_report_type:
            required_cols.add("report_type")
        if has_f_ann_date:
            required_cols.add("f_ann_date")
        elif "ann_date" not in report_income_df.columns:
            raise ValueError("report_transform_merge_now 缺少公告日期列（f_ann_date 或 ann_date）")
        missing = required_cols - set(report_income_df.columns)
        if missing:
            raise ValueError(f"report_transform_merge_now 缺少必要字段: {sorted(missing)}")

        df = report_income_df.copy()

        ann_col = "f_ann_date" if has_f_ann_date else "ann_date"
        group_cols = ["ts_code", "end_date"] + (["report_type"] if has_report_type else [])

        df["_update_flag_is_1"] = (df["update_flag"].astype(str) == "1").astype(int)
        df["_ann_date_norm"] = df[ann_col].fillna("").astype(str)

        df = df.sort_values(
            by=group_cols + ["_update_flag_is_1", "_ann_date_norm"],
            ascending=[True] * len(group_cols) + [False, False],
            kind="mergesort",
        )

        df = df.drop_duplicates(subset=group_cols, keep="first")

        if has_report_type:
            df["report_type"] = "merge_now"

        df = df.drop(columns=["_update_flag_is_1", "_ann_date_norm"], errors="ignore")

        dup_mask = df.duplicated(subset=group_cols, keep=False)
        if dup_mask.any():
            dup_df = df.loc[dup_mask, group_cols + ["update_flag"]]
            print(f"[错误] 清洗后仍存在重复 {group_cols}，示例：")
            print(dup_df.head(20).to_string(index=False))
            raise ValueError("report_transform_merge_now 清洗后仍存在重复维度数据")

        return df
    
    def report_period_generate(self, start_date: str, end_date: str) -> List[str]:
        """
        生成财报报告期列表

        参数说明
            start_date: 开始日期，格式 YYYYMMDD，如 "20240101"
            end_date: 结束日期，格式 YYYYMMDD，如 "20251231"

        返回说明
            report_period: 财报报告期列表，格式如 ["20240331", "20240630", "20240930", "20241231"]

        函数逻辑
            根据 start_date 和 end_date，生成该区间内所有季度末报告期；
            2005 年之前（不含）只生成半年报（0630）和年报（1231）；
            2005 年及之后生成完整四季报（0331/0630/0930/1231）。
        """
        if not start_date or not end_date or start_date > end_date:
            return []

        start_year = int(start_date[:4])
        end_year = int(end_date[:4])
        report_period = []

        for year in range(start_year, end_year + 1):
            qends = ("0630", "1231") if year < 2005 else self.QUARTER_END_DATES
            for qend in qends:
                period = f"{year}{qend}"
                if start_date <= period <= end_date:
                    report_period.append(period)

        return report_period

    def check_report_complete_by_end_dates(
        self,
        end_dates: list[str],
        start_end_date: str,
        end_end_date: str,
    ) -> list[str]:
        """
        在区间 [start_end_date, end_end_date] 内，按季度末序列（report_period_generate）对比已有报告期，
        返回缺失的报告期 end_date 列表（YYYYMMDD 字符串）。

        「应有」季度从 start_end_date 起算（调用方通常已传入 max(20050101, list_date)），
        与 end_dates 做差集；不根据已观测报告期调整起点。

        适用于利润表、现金流、资产负债表等任意「报告期列为季度末」的表：调用方只传入已存在的 end_date 集合即可。

        Args:
            end_dates: 已观测报告期，均为 YYYYMMDD 字符串（无空值、无首尾空格）。
            start_end_date: 区间起点 YYYYMMDD（与报告期字符串比较）。
            end_end_date: 区间终点 YYYYMMDD（含边界）。

        Returns:
            应有而未出现的季度末 end_date 列表，顺序与 report_period_generate 一致。
        """
        missing_periods: List[str]

        if not start_end_date or not end_end_date or start_end_date > end_end_date:
            missing_periods = []
            return missing_periods

        expected = self.report_period_generate(start_end_date, end_end_date)
        if not expected:
            missing_periods = []
            return missing_periods

        missing_periods = [ed for ed in expected if ed not in end_dates]
        return missing_periods

    @staticmethod
    def report_more_detail_to_json(data_model: Type[Any], tushare_data: pd.DataFrame) -> pd.DataFrame:
        """
        将 tushare 数据中非核心字段转换为 JSON 格式

        功能描述：
        从 tushare 中获取的财报数据，核心字段采用独立字段存储，其他字段生成 json 存储在 jsonb 字段。
        本函数用于将其他字段生成 json。

        Args:
            data_model: SQLAlchemy 模型类，例如 ReportIncome
            tushare_data: DataFrame 格式，tushare 返回的财报数据

        Returns:
            处理后的 DataFrame，包含：
            - 模型定义的字段（保留原值）
            - JSONB 字段（包含其他字段的 JSON 数据）

        逻辑：
        1. 识别 data_model 中定义的字段（排除 JSONB 字段）
        2. 在 tushare_data 中删除表结构中存在的字段
        3. 将剩下的字段，改成 json 格式，用于存储在 PostgreSQL 的 jsonb 格式字段中
        """
        if tushare_data.empty:
            return tushare_data

        model_columns = set()
        jsonb_column = None

        for col in data_model.__table__.columns:
            col_name = col.name
            col_type_str = str(col.type).upper()
            if "JSONB" in col_type_str or "JSON" in col_type_str:
                jsonb_column = col_name
            else:
                model_columns.add(col_name)

        if jsonb_column is None:
            raise ValueError(f"模型 {data_model.__name__} 中未找到 JSONB 类型字段，无法使用 data_to_json 函数")

        result_df = tushare_data.copy()
        tushare_columns = set(tushare_data.columns)
        json_columns = tushare_columns - model_columns - {jsonb_column}

        # to_dict(orient="records") 比 iterrows() 快 5-10×（避免每行构 Series 与 dtype 推断）
        if json_columns:
            json_records = tushare_data[list(json_columns)].to_dict(orient="records")
            json_data_list = [
                {
                    k: v
                    for k, v in record.items()
                    if v is not None
                    and not (isinstance(v, float) and pd.isna(v))
                    and not (isinstance(v, str) and v.strip() == "")
                }
                for record in json_records
            ]
        else:
            json_data_list = [{} for _ in range(len(tushare_data))]

        result_df[jsonb_column] = json_data_list
        columns_to_keep = (model_columns | {jsonb_column}) & set(result_df.columns)
        columns_to_drop = [col for col in result_df.columns if col not in columns_to_keep]
        if columns_to_drop:
            result_df = result_df.drop(columns=columns_to_drop)

        return result_df

    def filter_report_by_delist(
        self,
        period: str,
        report_df: pd.DataFrame,
        *,
        stock_extract: StockExtract | None = None,
    ) -> pd.DataFrame:
        """
        按报告期末日在市名单过滤财报：剔除该时点未在市（未上市或已退市）的股票。

        period、report_df 内的 end_date（若有）均为 8 位数字字符串 YYYYMMDD。
        report_df 须含 ts_code；若含 end_date，会先筛出等于本报告期的行。
        """

        if report_df is None or report_df.empty:
            return report_df.copy() if report_df is not None else pd.DataFrame()

        df = report_df.copy()
        if "end_date" in df.columns:
            df = df.loc[df["end_date"].astype(str) == str(period)]

        extractor = stock_extract if stock_extract is not None else StockExtract()
        listed = extractor.get_stock_list(period=str(period))
        allowed = {r.ts_code for r in listed if r.ts_code}
        if not allowed:
            return df.iloc[0:0].copy()

        return df.loc[df["ts_code"].astype(str).str.strip().isin(allowed)].copy()
