import { formatReportPeriod } from '@/utils/report-period';

export function formatOverviewDateKey(
  dateKey: string,
  dateKeyType: string,
): string {
  if (dateKeyType === 'month' && dateKey.length === 6) {
    return `${dateKey.slice(0, 4)}-${dateKey.slice(4, 6)}`;
  }
  return formatReportPeriod(dateKey);
}

export const groupStatusLabels: Record<string, string> = {
  healthy: '正常',
  warning: '关注',
  critical: '严重',
};

export const groupStatusColors: Record<string, string> = {
  healthy: 'success',
  warning: 'warning',
  critical: 'error',
};

export const keyPathStatusLabels: Record<string, string> = {
  ok: '正常',
  warning: '滞后',
  critical: '严重滞后',
  unknown: '未知',
};

export const keyPathStatusColors: Record<string, string> = {
  ok: 'success',
  warning: 'warning',
  critical: 'error',
  unknown: 'default',
};
