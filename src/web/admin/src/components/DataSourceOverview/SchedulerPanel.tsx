import { Card, Col, Row, Statistic, Typography } from 'antd';
import type { ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { Link } from 'react-router-dom';
import { scheduleRunColumns } from '@/pages/scheduler/runColumns';
import type {
  OverviewSchedulerRunItem,
  OverviewSchedulerSummary,
} from '@/types/dataSource';
import { formatDateTime } from '@/utils/datetime';

const { Title, Text } = Typography;

interface SchedulerPanelProps {
  scheduler: OverviewSchedulerSummary;
}

export default function SchedulerPanel({ scheduler }: SchedulerPanelProps) {
  const runColumns: ProColumns<OverviewSchedulerRunItem>[] = scheduleRunColumns;

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <Title level={5} style={{ marginBottom: 0 }}>
          调度摘要
        </Title>
        <Link to="/scheduler/runs">执行历史</Link>
      </div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic title="启用任务" value={scheduler.jobs_enabled_count} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="今日执行"
              value={scheduler.today_run_count}
              suffix={
                scheduler.today_run_count > 0
                  ? `成功 ${scheduler.today_success_count}`
                  : undefined
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card size="small">
            <Statistic
              title="最近执行"
              value={formatDateTime(scheduler.last_run_at) || '—'}
              valueStyle={{ fontSize: 16 }}
            />
          </Card>
        </Col>
      </Row>
      <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>
        最近 5 次执行
      </Text>
      <ProTable<OverviewSchedulerRunItem>
        columns={runColumns}
        rowKey="run_id"
        dataSource={scheduler.recent_runs}
        pagination={false}
        search={false}
        options={false}
        locale={{ emptyText: '暂无执行记录' }}
      />
    </div>
  );
}
