import { getDashboard } from '@/services/dataSource';
import { COMPLETENESS_THRESHOLD } from './taskFlashConstants';

export interface VerifyStepCompletenessParams {
  groupId: string;
  dateKey: string;
  columnKey: string;
  stepLabel: string;
  threshold?: number;
}

export async function verifyStepCompleteness(
  params: VerifyStepCompletenessParams,
): Promise<void> {
  const threshold = params.threshold ?? COMPLETENESS_THRESHOLD;
  const resp = await getDashboard({
    group_id: params.groupId,
    start: params.dateKey,
    end: params.dateKey,
    page: 1,
    count: 1,
  });
  const row = resp.items.find((item) => item.date_key === params.dateKey);
  if (!row) {
    throw new Error(
      `${params.stepLabel}：无法验证完整度，未找到日期 ${params.dateKey}`,
    );
  }
  const metric = row.columns[params.columnKey];
  if (!metric) {
    throw new Error(
      `${params.stepLabel}：无法验证完整度，未找到列 ${params.columnKey}`,
    );
  }
  if (metric.period_stock_count <= 0) {
    return;
  }
  const ratio =
    metric.ratio ?? metric.count / metric.period_stock_count;
  if (ratio < threshold) {
    throw new Error(
      `${params.stepLabel}：数据完整度 ${(ratio * 100).toFixed(1)}%（${metric.count}/${metric.period_stock_count}），低于 ${(threshold * 100).toFixed(0)}%`,
    );
  }
}
