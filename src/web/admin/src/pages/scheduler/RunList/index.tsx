import { Typography } from 'antd';
import { ProTable } from '@ant-design/pro-components';
import { listSchedulerRuns } from '@/services/scheduler';
import type { ScheduleRunItem } from '@/types/scheduler';
import { scheduleRunColumns } from '@/pages/scheduler/runColumns';

const { Title } = Typography;

const columns = [
  ...scheduleRunColumns,
  { title: '错误', dataIndex: 'error_message', ellipsis: true, search: false },
];

export default function SchedulerRunListPage() {
  return (
    <>
      <Title level={4} style={{ marginBottom: 16 }}>
        执行历史
      </Title>
      <ProTable<ScheduleRunItem>
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
          return { data: data.items, success: true, total: data.total };
        }}
        pagination={{ defaultPageSize: 20 }}
        search={{ labelWidth: 80 }}
        expandable={{
          expandedRowRender: (record) => (
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(record, null, 2)}
            </pre>
          ),
        }}
        options={{ reload: true, density: true }}
      />
    </>
  );
}
