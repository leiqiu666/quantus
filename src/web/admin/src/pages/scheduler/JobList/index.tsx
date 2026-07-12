import { Button, Popconfirm, Space, Switch, Typography } from 'antd';
import type { ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { useNavigate } from 'react-router-dom';
import { useSseTask } from '@/components/SseTask/useSseTask';
import {
  deleteSchedulerJob,
  getSchedulerJobs,
  updateSchedulerJob,
} from '@/services/scheduler';
import type { ScheduleJobItem } from '@/types/scheduler';
import { scheduleKindLabels } from '@/types/scheduler';

const { Title } = Typography;

export default function SchedulerJobListPage() {
  const navigate = useNavigate();
  const { startScheduleJob } = useSseTask();

  const columns: ProColumns<ScheduleJobItem>[] = [
    {
      title: '任务键',
      dataIndex: 'job_key',
      width: 180,
      copyable: true,
    },
    {
      title: '名称',
      dataIndex: 'name',
      width: 200,
    },
    {
      title: '周期',
      width: 140,
      search: false,
      render: (_, row) => (
        <span>
          {scheduleKindLabels[row.schedule_kind]} {row.schedule_time}
        </span>
      ),
    },
    {
      title: '仅交易日',
      dataIndex: 'run_on_trading_day',
      width: 100,
      search: false,
      render: (_, row) => (row.run_on_trading_day ? '是' : '否'),
    },
    {
      title: '命令数',
      dataIndex: 'command_count',
      width: 80,
      search: false,
    },
    {
      title: '启用',
      dataIndex: 'enabled',
      width: 80,
      search: false,
      render: (_, row, __, action) => (
        <Switch
          checked={row.enabled}
          onChange={async (checked) => {
            await updateSchedulerJob(row.job_key, { enabled: checked });
            action?.reload();
          }}
        />
      ),
    },
    {
      title: '操作',
      valueType: 'option',
      width: 220,
      render: (_, row, __, action) => (
        <Space>
          <Button type="link" onClick={() => navigate(`/scheduler/jobs/edit?key=${row.job_key}`)}>
            编辑
          </Button>
          <Button
            type="link"
            onClick={() => {
              startScheduleJob({ jobKey: row.job_key, name: row.name });
            }}
          >
            立即运行
          </Button>
          <Popconfirm
            title="确认删除？"
            onConfirm={async () => {
              await deleteSchedulerJob(row.job_key);
              action?.reload();
            }}
          >
            <Button type="link" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Title level={4} style={{ margin: 0 }}>
          调度任务
        </Title>
        <Button type="primary" onClick={() => navigate('/scheduler/jobs/edit')}>
          新建任务
        </Button>
      </Space>
      <ProTable<ScheduleJobItem>
        columns={columns}
        rowKey="job_key"
        request={async () => {
          const data = await getSchedulerJobs();
          return { data, success: true, total: data.length };
        }}
        pagination={false}
        search={false}
        options={{ reload: true, density: true }}
      />
    </>
  );
}
