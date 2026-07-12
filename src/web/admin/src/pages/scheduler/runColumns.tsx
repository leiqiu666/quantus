import { Tag } from 'antd';
import type { ProColumns } from '@ant-design/pro-components';
import type { ScheduleRunItem } from '@/types/scheduler';
import { formatScheduleRunStatus } from '@/types/scheduler';
import { formatDateTime } from '@/utils/datetime';

const statusColor: Record<string, string> = {
  success: 'green',
  failed: 'red',
  partial: 'orange',
  running: 'blue',
  skipped: 'default',
};

export const scheduleRunColumns: ProColumns<ScheduleRunItem>[] = [
  { title: 'Run ID', dataIndex: 'run_id', width: 80, search: false },
  { title: '任务', dataIndex: 'job_key', width: 160, search: false },
  { title: '触发', dataIndex: 'triggered_by', width: 80, search: false },
  {
    title: '状态',
    dataIndex: 'status',
    width: 90,
    search: false,
    render: (_, row) => (
      <Tag color={statusColor[row.status]}>{formatScheduleRunStatus(row.status)}</Tag>
    ),
  },
  {
    title: '开始',
    dataIndex: 'started_at',
    width: 170,
    search: false,
    render: (_, row) => formatDateTime(row.started_at),
  },
  {
    title: '结束',
    dataIndex: 'finished_at',
    width: 170,
    search: false,
    render: (_, row) => formatDateTime(row.finished_at),
  },
];
