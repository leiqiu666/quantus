import { Card, Col, Row, Statistic, Tag, Typography } from 'antd';
import type { ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { useEffect, useState } from 'react';
import { getSchedulerOverview } from '@/services/scheduler';
import type { ScheduleCommandItem, ScheduleOverviewResponse, ScheduleRunItem } from '@/types/scheduler';
import { scheduleHintLabels } from '@/types/scheduler';
import { scheduleRunColumns } from '@/pages/scheduler/runColumns';

const commandColumns: ProColumns<ScheduleCommandItem>[] = [
  {
    title: '命令',
    dataIndex: 'label',
    ellipsis: true,
    search: false,
  },
  {
    title: '分类',
    dataIndex: 'category',
    width: 90,
    valueType: 'select',
    valueEnum: {
      财报: { text: '财报' },
      基础: { text: '基础' },
      K线: { text: 'K线' },
      市场: { text: '市场' },
      财务: { text: '财务' },
      指数: { text: '指数' },
      仓库: { text: '仓库' },
    },
  },
  {
    title: '时机建议',
    dataIndex: 'schedule_hint',
    width: 100,
    search: false,
    render: (_, row) => scheduleHintLabels[row.schedule_hint],
  },
  {
    title: '已引用',
    dataIndex: 'is_referenced',
    width: 90,
    valueType: 'select',
    valueEnum: {
      true: { text: '是', status: 'Success' },
      false: { text: '否', status: 'Default' },
    },
    render: (_, row) =>
      row.is_referenced ? <Tag color="green">是</Tag> : <Tag>否</Tag>,
  },
  {
    title: '引用任务',
    dataIndex: 'referenced_by',
    search: false,
    render: (_, row) =>
      row.referenced_by.length ? row.referenced_by.join(', ') : '—',
  },
];

const { Title } = Typography;

export default function SchedulerOverviewPage() {
  const [overview, setOverview] = useState<ScheduleOverviewResponse | null>(null);

  useEffect(() => {
    getSchedulerOverview().then(setOverview).catch(console.error);
  }, []);

  return (
    <>
      <Title level={4} style={{ marginBottom: 16 }}>
        调度看板
      </Title>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title="命令总数" value={overview?.command_total ?? '—'} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已引用"
              value={overview?.command_referenced_count ?? '—'}
              suffix={`/ ${overview?.command_total ?? '—'}`}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="未引用" value={overview?.command_unreferenced_count ?? '—'} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="启用任务" value={overview?.jobs_enabled_count ?? '—'} />
          </Card>
        </Col>
      </Row>

      <Title level={5}>最近执行</Title>
      <ProTable<ScheduleRunItem>
        columns={scheduleRunColumns}
        rowKey="run_id"
        dataSource={overview?.recent_runs ?? []}
        pagination={false}
        search={false}
        options={false}
        style={{ marginBottom: 24 }}
      />

      <Title level={5}>命令覆盖</Title>
      <ProTable<ScheduleCommandItem>
        columns={commandColumns}
        rowKey="command_key"
        dataSource={overview?.commands ?? []}
        pagination={false}
        search={{ labelWidth: 80 }}
        options={{ reload: false, density: true }}
        toolBarRender={() => []}
      />
    </>
  );
}
