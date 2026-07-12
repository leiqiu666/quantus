import { Button, Modal, Space, Tag, Typography } from 'antd';
import type { ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { Link } from 'react-router-dom';
import { dateKeyToSseRange } from '@/components/DataSourceDashboard/dateKeySse';
import { useSseTask } from '@/components/SseTask';
import type { OverviewGapItem, OverviewGroupItem } from '@/types/dataSource';
import { formatOverviewDateKey } from './formatDateKey';

const { Text } = Typography;

interface GapTodoTableProps {
  gaps: OverviewGapItem[];
  groups: OverviewGroupItem[];
}

function ratioTagColor(ratio: number | null, threshold: number): string {
  if (ratio == null) {
    return 'default';
  }
  if (ratio >= threshold) {
    return 'success';
  }
  if (ratio >= threshold - 0.05) {
    return 'orange';
  }
  return 'error';
}

export default function GapTodoTable({ gaps, groups }: GapTodoTableProps) {
  const { startEtlTask, guardEtlTask } = useSseTask();
  const pathByGroup = Object.fromEntries(
    groups.map((g) => [g.group_id, g.detail_path]),
  );

  const handleFill = (row: OverviewGapItem) => {
    if (!row.sse_task_key) {
      return;
    }
    const range = dateKeyToSseRange(row.date_key, row.date_key_type);
    const dateDisplay = formatOverviewDateKey(row.date_key, row.date_key_type);
    if (
      !guardEtlTask({
        taskKey: row.sse_task_key,
        startDate: range.startDate,
        endDate: range.endDate,
      })
    ) {
      return;
    }
    Modal.confirm({
      title: `补位：${row.column_label}`,
      content: `${row.group_title} · ${dateDisplay}`,
      okText: '开始',
      cancelText: '取消',
      onOk: () => {
        startEtlTask({
          taskKey: row.sse_task_key,
          label: row.column_label,
          startDate: range.startDate,
          endDate: range.endDate,
        });
      },
    });
  };

  const columns: ProColumns<OverviewGapItem>[] = [
    {
      title: '分组',
      dataIndex: 'group_title',
      width: 140,
      render: (_, row) => {
        const path = pathByGroup[row.group_id];
        const to = path ? `${path}?focus=${row.date_key}` : '#';
        return path ? <Link to={to}>{row.group_title}</Link> : row.group_title;
      },
    },
    {
      title: '日期',
      dataIndex: 'date_key',
      width: 120,
      render: (_, row) => formatOverviewDateKey(row.date_key, row.date_key_type),
    },
    {
      title: '数据源',
      dataIndex: 'column_label',
      width: 120,
    },
    {
      title: '完整率',
      dataIndex: 'ratio',
      width: 100,
      render: (_, row) => {
        if (row.ratio == null) {
          return '—';
        }
        const label = `${(row.ratio * 100).toFixed(1)}%`;
        return (
          <Tag color={ratioTagColor(row.ratio, row.threshold)}>{label}</Tag>
        );
      },
    },
    {
      title: '操作',
      width: 140,
      render: (_, row) => {
        const path = pathByGroup[row.group_id];
        return (
          <Space size="small">
            {row.sse_task_key ? (
              <Button type="link" size="small" onClick={() => handleFill(row)}>
                补位
              </Button>
            ) : null}
            {path ? (
              <Link to={`${path}?focus=${row.date_key}`}>明细</Link>
            ) : null}
          </Space>
        );
      },
    },
  ];

  return (
    <div>
      <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
        窗口内未达标单元格 Top {gaps.length}
      </Text>
      <ProTable<OverviewGapItem>
        columns={columns}
        rowKey={(row) =>
          `${row.group_id}:${row.date_key}:${row.column_key}`
        }
        dataSource={gaps}
        pagination={false}
        search={false}
        options={false}
        locale={{ emptyText: '窗口内无缺口' }}
      />
    </div>
  );
}
