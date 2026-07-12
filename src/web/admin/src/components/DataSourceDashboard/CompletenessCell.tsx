import { Modal, Tag, Tooltip } from 'antd';
import { useSseTask } from '@/components/SseTask';
import type { ColumnMetric, DashboardColumnMeta } from '@/types/dataSource';
import { dateKeyToSseRange } from './dateKeySse';

interface CompletenessCellProps {
  metric: ColumnMetric;
  column: DashboardColumnMeta;
  dateKey: string;
  dateKeyType: string;
  dateDisplay: string;
}

function ratioTagColor(ratio: number | null, hasSnapshot: boolean): string {
  if (!hasSnapshot || ratio == null || ratio <= 0) {
    return 'default';
  }
  const pct = ratio * 100;
  if (pct >= 95) {
    return 'success';
  }
  if (pct >= 90) {
    return 'orange';
  }
  return 'error';
}

function ratioLabel(ratio: number | null, hasSnapshot: boolean): string {
  if (!hasSnapshot || ratio == null) {
    return '0.0%';
  }
  return `${(ratio * 100).toFixed(1)}%`;
}

export default function CompletenessCell({
  metric,
  column,
  dateKey,
  dateKeyType,
  dateDisplay,
}: CompletenessCellProps) {
  const { startEtlTask, guardEtlTask } = useSseTask();
  const showRatio = metric.period_stock_count > 0;
  const canRefresh = Boolean(column.sse_task_key);

  const handleRefresh = () => {
    if (!column.sse_task_key) {
      return;
    }
    const range = dateKeyToSseRange(dateKey, dateKeyType);
    if (
      !guardEtlTask({
        taskKey: column.sse_task_key,
        startDate: range.startDate,
        endDate: range.endDate,
      })
    ) {
      return;
    }
    Modal.confirm({
      title: `补位：${column.label}`,
      content: dateDisplay,
      okText: '开始',
      cancelText: '取消',
      onOk: () => {
        startEtlTask({
          taskKey: column.sse_task_key,
          label: column.label,
          startDate: range.startDate,
          endDate: range.endDate,
        });
      },
    });
  };

  if (!showRatio) {
    return <span>{metric.count}</span>;
  }

  const label = ratioLabel(metric.ratio, metric.has_snapshot);
  const color = ratioTagColor(metric.ratio, metric.has_snapshot);

  const tag = (
    <Tag
      color={color}
      className={canRefresh ? 'cursor-pointer' : undefined}
      onClick={
        canRefresh
          ? (e) => {
              e.stopPropagation();
              handleRefresh();
            }
          : undefined
      }
    >
      {label}
    </Tag>
  );

  return (
    <span className="inline-flex items-center gap-1.5">
      <span>{metric.count}</span>
      {canRefresh ? <Tooltip title="补位">{tag}</Tooltip> : tag}
    </span>
  );
}
