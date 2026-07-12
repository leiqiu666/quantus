from src.service.financial.financial_report_income_service import ReportIncomeService
from src.common.function import report_period_generate
from datetime import datetime

class ReportIncomeCollect:
    def __init__(self):
        self.report_income_service = ReportIncomeService()
        self.today = datetime.now().strftime("%Y%m%d")
    
    def collect_report_income_by_period(self, start_date: str, end_date: str):
        # 生成财报报告期列表
        report_period = report_period_generate(start_date, end_date)
        period_count = len(report_period)
        print(f"收集财报数据期数: {period_count}")
        for index, period in enumerate(report_period):
            print(f"当前进度 {index+1}-1/{period_count} 收集财报数据【1-合并报表】: {period}")
            self.report_service.collect_report_income_by_tushare(period=period,report_type=1)
            print(f"当前进度 {index+1}-2/{period_count} 收集财报数据【2-单季合并报表】: {period}")
            self.report_service.collect_report_income_by_tushare(period=period,report_type=2)
            print(f"当前进度 {index+1}-3/{period_count} 收集财报数据【3-调整单季合并报表】: {period}")
            self.report_service.collect_report_income_by_tushare(period=period,report_type=3)
            print(f"当前进度 {index+1}-4/{period_count} 收集财报数据【4-调整合并报表】: {period}")
            self.report_service.collect_report_income_by_tushare(period=period,report_type=4)
            print(f"当前进度 {index+1}-5/{period_count} 收集财报数据【5-调整前合并报表】: {period}")
            self.report_service.collect_report_income_by_tushare(period=period,report_type=5)
            print(f"当前进度 {index+1}-6/{period_count} 收集财报数据【6-母公司报表】: {period}")
            self.report_service.collect_report_income_by_tushare(period=period,report_type=6)
            print(f"当前进度 {index+1}-7/{period_count} 收集财报数据【7-母公司单季报表】: {period}")
            self.report_service.collect_report_income_by_tushare(period=period,report_type=7)
            print(f"当前进度 {index+1}-8/{period_count} 收集财报数据【8-母公司调整单季表】: {period}")
            self.report_service.collect_report_income_by_tushare(period=period,report_type=8)
            print(f"当前进度 {index+1}-9/{period_count} 收集财报数据【9-母公司调整表】: {period}")
            self.report_service.collect_report_income_by_tushare(period=period,report_type=9)
            print(f"当前进度 {index+1}-10/{period_count} 收集财报数据【10-母公司调整前报表】: {period}")
            self.report_service.collect_report_income_by_tushare(period=period,report_type=10)
            print(f"当前进度 {index+1}-11/{period_count} 收集财报数据【11-母公司调整前合并报表】: {period}")
            self.report_service.collect_report_income_by_tushare(period=period,report_type=11)
            print(f"当前进度 {index+1}-12/{period_count} 收集财报数据【12-母公司调整前报表】: {period}")
            self.report_service.collect_report_income_by_tushare(period=period,report_type=12)

    def collect_report_income_init(self):
        # 获取今日日期字符串 20260315
            today = datetime.now().strftime("%Y%m%d")
            self.collect_report_income_by_period(start_date='20250901', end_date='20251001')

    def collect_report_income_merge_data_clean_init(self, start_date: str, end_date: str):
        # 获取今日日期字符串 20260315
            today = self.today
            report_period = report_period_generate(start_date, end_date)
            self.report_income_service.report_income_merge_data_clean(report_type="1", report_type_new="merge_now", period_list=report_period)

if __name__ == "__main__":
    report_income_collect = ReportIncomeCollect()
    # ts_code="000001.SZ", start_date="20230331", end_date="20240331"
    #report_income = report_collect.collect_report_income_by_code(ts_code="000001.SZ", start_date="20230331", end_date="20240331")
    #report_income = report_income_collect.collect_report_income_init()
    report_income = report_income_collect.collect_report_income_merge_data_clean(start_date='20250901', end_date='20251001')
    print(report_income)