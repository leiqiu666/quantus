import type {
  FinancialReportTaskType,
  ReportPeriodItem,
  ReportPeriodListRequest,
} from '@/types/financial';
import { requestJson } from '@/utils/request';

const FINANCIAL_PREFIX = '/api/admin/financial/report';

export const FINANCIAL_SSE_ENDPOINTS: Record<FinancialReportTaskType, string> =
  {
    income: `${FINANCIAL_PREFIX}/income-history-init`,
    balance: `${FINANCIAL_PREFIX}/balance-history-init`,
    cashflow: `${FINANCIAL_PREFIX}/cashflow-history-init`,
    indicator: `${FINANCIAL_PREFIX}/indicator-history-init`,
  };

export const FINANCIAL_TASK_LABELS: Record<FinancialReportTaskType, string> = {
  income: '更新利润表',
  balance: '更新资产负债表',
  cashflow: '更新现金流量表',
  indicator: '更新财务指标',
};

export function getReportPeriodList(
  params: ReportPeriodListRequest,
): Promise<ReportPeriodItem[]> {
  return requestJson<ReportPeriodItem[]>(`${FINANCIAL_PREFIX}/period-list`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
}
