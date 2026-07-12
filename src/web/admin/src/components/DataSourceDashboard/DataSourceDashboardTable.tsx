import { useEffect, useRef, useState } from 'react';
import { message, Modal, Typography } from 'antd';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import dayjs from 'dayjs';
import { useSearchParams } from 'react-router-dom';
import CompletenessCell from './CompletenessCell';
import HeaderRefreshIcon from './HeaderRefreshIcon';
import RowRefreshButton from './RowRefreshButton';
import { dateKeyToSseRange, searchRangeToSseRange } from './dateKeySse';
import {
  ETL_TASK_DUPLICATE_MESSAGE,
  ROW_SEQUENCE_DUPLICATE_MESSAGE,
  findActiveEtlTask,
  findActiveRowSequence,
  useSseTask,
} from '@/components/SseTask';
import { getDashboard } from '@/services/dataSource';
import { useAppSelector } from '@/store/hooks';
import type { DashboardColumnMeta, DashboardRow } from '@/types/dataSource';
import { formatReportPeriod, todayYmd } from '@/utils/report-period';

const { Title } = Typography;

function toYmd(value: unknown): string | undefined {
  if (!value) {
    return undefined;
  }
  if (dayjs.isDayjs(value)) {
    return value.format('YYYYMMDD');
  }
  if (typeof value === 'string') {
    return dayjs(value).format('YYYYMMDD');
  }
  return undefined;
}

function toYyyymm(value: unknown): string | undefined {
  const ymd = toYmd(value);
  return ymd ? ymd.slice(0, 6) : undefined;
}

interface DataSourceDashboardTableProps {
  groupId: string;
  title?: string;
}

export default function DataSourceDashboardTable({
  groupId,
  title,
}: DataSourceDashboardTableProps) {
  const actionRef = useRef<ActionType>(null);
  const [searchParams] = useSearchParams();
  const focusDateKey = searchParams.get('focus') ?? undefined;
  const [columnsMeta, setColumnsMeta] = useState<DashboardColumnMeta[]>([]);
  const [dateLabel, setDateLabel] = useState('日期');
  const [dateKeyType, setDateKeyType] = useState<string>('trade_date');
  const rangeDefaultsRef = useRef<{ start: string; end: string } | null>(null);
  const [searchRange, setSearchRange] = useState<{ start: string; end: string } | null>(
    null,
  );
  const { startEtlTask, startRowSequenceTask, guardEtlTask } = useSseTask();
  const tasks = useAppSelector((s) => s.sseTask.tasks);
  const reloadedTaskIds = useRef<Set<string>>(new Set());

  useEffect(() => {
    for (const task of tasks) {
      const isFinished =
        task.status === 'success' ||
        (task.status === 'error' && task.mode === 'row_sequence');
      if (!isFinished) {
        continue;
      }
      if (reloadedTaskIds.current.has(task.id)) {
        continue;
      }
      reloadedTaskIds.current.add(task.id);
      actionRef.current?.reload();
    }
  }, [tasks]);

  const formatDateKey = (key: string) => {
    if (dateKeyType === 'month' && key.length === 6) {
      return `${key.slice(0, 4)}-${key.slice(4, 6)}`;
    }
    return formatReportPeriod(key);
  };

  const pullableColumns = columnsMeta.filter((c) => c.sse_task_key);

  const handleColumnRefresh = (col: DashboardColumnMeta) => {
    if (!col.sse_task_key) {
      return;
    }
    const rangeStart =
      searchRange?.start ?? rangeDefaultsRef.current?.start;
    const rangeEnd =
      searchRange?.end ?? rangeDefaultsRef.current?.end ?? todayYmd();
    if (!rangeStart) {
      message.warning('看板区间尚未加载，请稍后再试');
      return;
    }
    const sseRange = searchRangeToSseRange(
      rangeStart,
      rangeEnd,
      dateKeyType,
    );
    if (
      !guardEtlTask({
        taskKey: col.sse_task_key,
        startDate: sseRange.startDate,
        endDate: sseRange.endDate,
      })
    ) {
      return;
    }
    Modal.confirm({
      title: `补位：${col.label}`,
      content: `区间 ${sseRange.startDate} ~ ${sseRange.endDate}`,
      okText: '开始',
      cancelText: '取消',
      onOk: () => {
        startEtlTask({
          taskKey: col.sse_task_key,
          label: col.label,
          startDate: sseRange.startDate,
          endDate: sseRange.endDate,
        });
      },
    });
  };

  const handleRowRefresh = (record: DashboardRow) => {
    if (pullableColumns.length === 0) {
      return;
    }
    const dateDisplay = formatDateKey(record.date_key);
    const range = dateKeyToSseRange(record.date_key, dateKeyType);
    if (
      findActiveRowSequence(tasks, range.startDate, range.endDate)
    ) {
      message.warning(ROW_SEQUENCE_DUPLICATE_MESSAGE);
      return;
    }
    const columnsToRun = pullableColumns.filter(
      (col) =>
        !findActiveEtlTask(
          tasks,
          col.sse_task_key,
          range.startDate,
          range.endDate,
        ),
    );
    if (columnsToRun.length === 0) {
      message.warning(ETL_TASK_DUPLICATE_MESSAGE);
      return;
    }
    Modal.confirm({
      title: `补位：${dateDisplay}`,
      content: `共 ${columnsToRun.length} 步：${columnsToRun.map((c) => c.label).join(' → ')}`,
      okText: '开始',
      cancelText: '取消',
      onOk: () => {
        const started = startRowSequenceTask({
          name: `补位：${dateDisplay}`,
          startDate: range.startDate,
          endDate: range.endDate,
          dashboardGroupId: groupId,
          dashboardDateKey: record.date_key,
          steps: columnsToRun.map((col) => ({
            taskKey: col.sse_task_key!,
            label: col.label,
            startDate: range.startDate,
            endDate: range.endDate,
            columnKey: col.key,
            threshold: col.threshold,
          })),
        });
        if (started) {
          message.info('已启动行级补位任务');
        }
      },
    });
  };

  const dynamicColumns: ProColumns<DashboardRow>[] = columnsMeta.map((col) => ({
    title: (
      <span className="inline-flex items-center gap-1">
        {col.label}
        {col.sse_task_key ? (
          <HeaderRefreshIcon onClick={() => handleColumnRefresh(col)} />
        ) : null}
      </span>
    ),
    dataIndex: ['columns', col.key],
    search: false,
    width: 150,
    align: 'left',
    render: (_, record) => {
      const metric = record.columns[col.key];
      if (!metric) {
        return '—';
      }
      return (
        <CompletenessCell
          metric={metric}
          column={col}
          dateKey={record.date_key}
          dateKeyType={dateKeyType}
          dateDisplay={formatDateKey(record.date_key)}
        />
      );
    },
  }));

  const formatDefaultStartLabel = () => {
    const start = rangeDefaultsRef.current?.start;
    if (!start) {
      return dateKeyType === 'month' ? '默认起点' : '默认起点';
    }
    if (dateKeyType === 'month' && start.length === 6) {
      return `${start.slice(0, 4)}-${start.slice(4, 6)}`;
    }
    if (start.length === 8) {
      return `${start.slice(0, 4)}-${start.slice(4, 6)}-${start.slice(6, 8)}`;
    }
    return start;
  };

  const tableColumns: ProColumns<DashboardRow>[] = [
    {
      title: `${dateLabel}起始`,
      dataIndex: 'start',
      valueType: dateKeyType === 'month' ? 'dateMonth' : 'date',
      hideInTable: true,
      fieldProps: { placeholder: formatDefaultStartLabel() },
    },
    {
      title: `${dateLabel}截止`,
      dataIndex: 'end',
      valueType: dateKeyType === 'month' ? 'dateMonth' : 'date',
      hideInTable: true,
      fieldProps: { placeholder: '默认今天' },
    },
    {
      title: dateLabel,
      dataIndex: 'date_key',
      search: false,
      width: 140,
      fixed: 'left',
      align: 'left',
      render: (_, record) => (
        <span className="inline-flex items-center">
          {pullableColumns.length > 0 ? (
            <>
              <RowRefreshButton onClick={() => handleRowRefresh(record)} />
              <span className="w-1.5 shrink-0" />
            </>
          ) : null}
          {formatDateKey(record.date_key)}
        </span>
      ),
    },
    {
      title: '活跃股票数',
      dataIndex: 'period_stock_count',
      search: false,
      width: 110,
      align: 'left',
      hideInTable: dateKeyType === 'month' || groupId === 'stock_basic_trade_date',
      render: (_, record) => record.period_stock_count ?? '—',
    },
    ...dynamicColumns,
  ];

  return (
    <div className="space-y-4">
      <Title level={3} style={{ marginBottom: 0 }}>
        {title ?? groupId}
      </Title>
      <ProTable<DashboardRow>
        actionRef={actionRef}
        rowKey="date_key"
        columns={tableColumns}
        cardBordered
        search={{ labelWidth: 'auto' }}
        options={{ density: true, reload: true }}
        pagination={{
          defaultPageSize: 50,
          showSizeChanger: true,
          pageSizeOptions: [20, 50, 100],
        }}
        scroll={{ x: 'max-content' }}
        rowClassName={(record) =>
          focusDateKey && record.date_key === focusDateKey
            ? 'bg-amber-50'
            : ''
        }
        request={async (params) => {
          const isMonth = dateKeyType === 'month';
          const fallbackStart = rangeDefaultsRef.current?.start;
          const fallbackEnd = rangeDefaultsRef.current?.end ?? todayYmd();
          const startBound = isMonth
            ? (toYyyymm(params.start) ?? (fallbackStart ? fallbackStart.slice(0, 6) : undefined))
            : (toYmd(params.start) ?? fallbackStart ?? undefined);
          const endBound = isMonth
            ? (toYyyymm(params.end) ?? (fallbackEnd ? fallbackEnd.slice(0, 6) : undefined))
            : (toYmd(params.end) ?? fallbackEnd ?? undefined);

          try {
            const data = await getDashboard({
              group_id: groupId,
              start: startBound,
              end: endBound,
              page: params.current ?? 1,
              count: params.pageSize ?? 50,
            });
            setColumnsMeta(data.meta.columns);
            setDateLabel(data.meta.date_label);
            setDateKeyType(data.meta.date_key_type);
            rangeDefaultsRef.current = {
              start: data.meta.default_start,
              end: data.meta.default_end,
            };
            const effectiveStart =
              startBound ?? data.meta.default_start ?? todayYmd();
            const effectiveEnd =
              endBound ?? data.meta.default_end ?? todayYmd();
            setSearchRange({ start: effectiveStart, end: effectiveEnd });
            return {
              data: data.items,
              success: true,
              total: data.total,
            };
          } catch {
            return { data: [], success: false, total: 0 };
          }
        }}
      />
    </div>
  );
}
