import { Col, Row, Segmented, Spin, Typography } from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';
import GroupHealthCard from '@/components/DataSourceOverview/GroupHealthCard';
import GapTodoTable from '@/components/DataSourceOverview/GapTodoTable';
import KeyPathPanel from '@/components/DataSourceOverview/KeyPathPanel';
import OverviewStats from '@/components/DataSourceOverview/OverviewStats';
import SchedulerPanel from '@/components/DataSourceOverview/SchedulerPanel';
import { useAppSelector } from '@/store/hooks';
import { getOverview } from '@/services/dataSource';
import type { OverviewResponse } from '@/types/dataSource';

const { Title } = Typography;

const WINDOW_OPTIONS = [
  { label: '5 条', value: 5 },
  { label: '10 条', value: 10 },
  { label: '20 条', value: 20 },
];

export default function OverviewPage() {
  const [window, setWindow] = useState(5);
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const tasks = useAppSelector((s) => s.sseTask.tasks);
  const reloadedTaskIds = useRef<Set<string>>(new Set());

  const load = useCallback(async (w: number) => {
    setLoading(true);
    try {
      const resp = await getOverview(w);
      setData(resp);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(window);
  }, [window, load]);

  useEffect(() => {
    for (const task of tasks) {
      if (task.status !== 'success') {
        continue;
      }
      if (reloadedTaskIds.current.has(task.id)) {
        continue;
      }
      reloadedTaskIds.current.add(task.id);
      load(window);
    }
  }, [tasks, window, load]);

  return (
    <Spin spinning={loading && !data}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <Title level={3} style={{ marginBottom: 0 }}>
          数据总览
        </Title>
        <Segmented
          options={WINDOW_OPTIONS}
          value={window}
          onChange={(v) => setWindow(v as number)}
        />
      </div>

      <OverviewStats data={data} loading={loading && !data} />

      <Title level={5} style={{ marginTop: 24, marginBottom: 12 }}>
        分组健康
      </Title>
      <Row gutter={[16, 16]}>
        {(data?.groups ?? []).map((group) => (
          <Col xs={24} sm={12} lg={8} key={group.group_id}>
            <GroupHealthCard group={group} />
          </Col>
        ))}
      </Row>

      <Title level={5} style={{ marginTop: 24, marginBottom: 12 }}>
        待处理缺口
      </Title>
      <GapTodoTable gaps={data?.gaps ?? []} groups={data?.groups ?? []} />

      <div style={{ marginTop: 24 }}>
        <KeyPathPanel
          items={data?.key_paths ?? []}
          referenceDate={data?.latest_trade_date ?? null}
        />
      </div>

      {data?.scheduler ? (
        <div style={{ marginTop: 24 }}>
          <SchedulerPanel scheduler={data.scheduler} />
        </div>
      ) : null}
    </Spin>
  );
}
