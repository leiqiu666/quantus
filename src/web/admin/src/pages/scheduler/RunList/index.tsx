import { Button, Space, Table, Tag, Typography, message } from 'antd';
import { ProTable } from '@ant-design/pro-components';
import { useRef, useState } from 'react';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { useSseTask } from '@/components/SseTask/useSseTask';
import {
  cancelSchedulerRun,
  getSchedulerRun,
  listSchedulerRuns,
} from '@/services/scheduler';
import type { ScheduleRunItem, ScheduleRunStepItem } from '@/types/scheduler';
import { formatScheduleRunStatus } from '@/types/scheduler';
import { scheduleRunColumns } from '@/pages/scheduler/runColumns';
import { formatDateTime } from '@/utils/datetime';

const { Title, Text } = Typography;

const stepStatusColor: Record<string, string> = {
  success: 'green',
  failed: 'red',
  running: 'blue',
  cancelled: 'default',
};

function StepProgress({ steps }: { steps: ScheduleRunStepItem[] }) {
  if (!steps.length) {
    return <Text type="secondary">暂无步骤</Text>;
  }
  return (
    <Table<ScheduleRunStepItem>
      size="small"
      pagination={false}
      rowKey="step_id"
      dataSource={steps}
      columns={[
        { title: '#', dataIndex: 'sort_order', width: 50 },
        { title: '命令', dataIndex: 'command_key' },
        {
          title: '状态',
          dataIndex: 'status',
          width: 90,
          render: (status: string) => (
            <Tag color={stepStatusColor[status] ?? 'default'}>
              {formatScheduleRunStatus(status)}
            </Tag>
          ),
        },
        {
          title: '写入',
          dataIndex: 'saved_count',
          width: 80,
          render: (v) => v ?? '—',
        },
        { title: '说明', dataIndex: 'message', ellipsis: true },
        {
          title: '开始',
          dataIndex: 'started_at',
          width: 160,
          render: (v) => formatDateTime(v),
        },
        {
          title: '结束',
          dataIndex: 'finished_at',
          width: 160,
          render: (v) => formatDateTime(v),
        },
      ]}
    />
  );
}

export default function SchedulerRunListPage() {
  const actionRef = useRef<ActionType>(undefined);
  const { startScheduleJob } = useSseTask();
  const [stoppingId, setStoppingId] = useState<number | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Record<number, ScheduleRunStepItem[]>>(
    {},
  );

  const columns: ProColumns<ScheduleRunItem>[] = [
    ...scheduleRunColumns,
    { title: '错误', dataIndex: 'error_message', ellipsis: true, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 160,
      render: (_, row) => {
        const isRunning = row.status === 'running';
        return (
          <Space size={4}>
            <Button
              type="link"
              size="small"
              disabled={!row.job_key || isRunning}
              onClick={() => {
                if (!row.job_key) {
                  message.warning('缺少任务键，无法重新执行');
                  return;
                }
                startScheduleJob({
                  jobKey: row.job_key,
                  name: row.job_key,
                });
                message.success('已开始重新执行');
                actionRef.current?.reload();
              }}
            >
              重新执行
            </Button>
            <Button
              type="link"
              danger
              size="small"
              disabled={!isRunning}
              loading={stoppingId === row.run_id}
              onClick={async () => {
                setStoppingId(row.run_id);
                try {
                  const res = await cancelSchedulerRun(row.run_id);
                  message.success(res.message || '已停止');
                  actionRef.current?.reload();
                } catch (err) {
                  message.error(err instanceof Error ? err.message : '停止失败');
                } finally {
                  setStoppingId(null);
                }
              }}
            >
              停止
            </Button>
          </Space>
        );
      },
    },
  ];

  return (
    <>
      <Space style={{ marginBottom: 16 }} align="baseline">
        <Title level={4} style={{ margin: 0 }}>
          执行历史
        </Title>
        <Text type="secondary">展开可看步骤进度；运行中可停止，结束后可重新执行</Text>
      </Space>
      <ProTable<ScheduleRunItem>
        actionRef={actionRef}
        columns={columns}
        rowKey="run_id"
        request={async (params) => {
          const page = params.current ?? 1;
          const count = params.pageSize ?? 20;
          const data = await listSchedulerRuns({
            job_key: params.job_key as string | undefined,
            page,
            count,
          });
          // 刷新已展开行的步骤，便于看进度
          const runningIds = data.items
            .filter((r) => r.status === 'running')
            .map((r) => r.run_id);
          if (runningIds.length) {
            void Promise.all(
              runningIds.map(async (id) => {
                try {
                  const detail = await getSchedulerRun(id);
                  setExpandedSteps((prev) => ({
                    ...prev,
                    [id]: detail.steps ?? [],
                  }));
                } catch {
                  /* ignore poll errors */
                }
              }),
            );
          }
          return { data: data.items, success: true, total: data.total };
        }}
        pagination={{ defaultPageSize: 20 }}
        search={{ labelWidth: 80 }}
        polling={3000}
        expandable={{
          onExpand: async (expanded, record) => {
            if (!expanded) return;
            try {
              const detail = await getSchedulerRun(record.run_id);
              setExpandedSteps((prev) => ({
                ...prev,
                [record.run_id]: detail.steps ?? [],
              }));
            } catch {
              message.error('加载步骤失败');
            }
          },
          expandedRowRender: (record) => (
            <StepProgress steps={expandedSteps[record.run_id] ?? record.steps ?? []} />
          ),
        }}
        options={{ reload: true, density: true }}
      />
    </>
  );
}
