import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button,
  Form,
  Input,
  Select,
  Space,
  Tabs,
  Typography,
  message,
} from 'antd';
import type { ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { useSearchParams } from 'react-router-dom';
import { getBacktestTable, listBacktestRuns } from '@/services/quant';
import type { BacktestRunItem, BacktestTableResponse } from '@/types/quant';

const { Title, Paragraph } = Typography;

type TableName = 'portfolio' | 'trades' | 'returns';

export default function BacktestTradesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [runs, setRuns] = useState<BacktestRunItem[]>([]);
  const [runId, setRunId] = useState(searchParams.get('run_id') || '');
  const [tab, setTab] = useState<TableName>('portfolio');
  const [tradeDate, setTradeDate] = useState('');
  const [groupId, setGroupId] = useState('');
  const [tsCode, setTsCode] = useState('');
  const [table, setTable] = useState<BacktestTableResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void listBacktestRuns(100)
      .then(setRuns)
      .catch(() => message.error('加载回测历史失败'));
  }, []);

  useEffect(() => {
    const q = searchParams.get('run_id');
    if (q) setRunId(q);
  }, [searchParams]);

  const load = useCallback(async () => {
    if (!runId.trim()) {
      message.warning('请选择 run_id');
      return;
    }
    setLoading(true);
    try {
      const data = await getBacktestTable(runId.trim(), {
        name: tab,
        trade_date: tradeDate.trim() || undefined,
        group_id: groupId.trim() || undefined,
        ts_code: tsCode.trim() || undefined,
        limit: 5000,
      });
      setTable(data);
      if (searchParams.get('run_id') !== runId.trim()) {
        setSearchParams({ run_id: runId.trim() });
      }
      if (data.total > data.rows.length) {
        message.info(`共 ${data.total} 行，已截断至 ${data.rows.length}`);
      }
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载失败');
      setTable(null);
    } finally {
      setLoading(false);
    }
  }, [runId, tab, tradeDate, groupId, tsCode, setSearchParams, searchParams]);

  useEffect(() => {
    if (runId) void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, runId]);

  const columns: ProColumns<Record<string, unknown>>[] = useMemo(() => {
    if (!table?.columns?.length) return [];
    return table.columns.map((c) => ({
      title: c,
      dataIndex: c,
      ellipsis: true,
      width: c === 'ts_code' || c === 'trade_date' ? 120 : 110,
      render: (_, r) => {
        const v = r[c];
        if (typeof v === 'number') return Number(v).toFixed(6);
        return v == null ? '-' : String(v);
      },
    }));
  }, [table]);

  return (
    <>
      <Title level={4} style={{ marginBottom: 8 }}>
        回测明细
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        查看某次 run 的持仓 / 成交 / 日收益 Parquet。可从回测详情「打开明细表」跳入。
      </Paragraph>

      <Form layout="inline" style={{ marginBottom: 12, rowGap: 12 }}>
        <Form.Item label="run_id">
          <Select
            showSearch
            allowClear
            style={{ width: 360 }}
            placeholder="选择历史 run"
            value={runId || undefined}
            onChange={(v) => setRunId(v || '')}
            options={runs.map((r) => ({
              label: `${r.run_id} · ${r.factor_name || r.combo_name || r.backtest_mode}`,
              value: r.run_id,
            }))}
          />
        </Form.Item>
        <Form.Item label="交易日">
          <Input
            value={tradeDate}
            onChange={(e) => setTradeDate(e.target.value)}
            placeholder="YYYYMMDD"
            style={{ width: 120 }}
          />
        </Form.Item>
        <Form.Item label="分组">
          <Input
            value={groupId}
            onChange={(e) => setGroupId(e.target.value)}
            placeholder="G0"
            style={{ width: 80 }}
          />
        </Form.Item>
        <Form.Item label="代码">
          <Input
            value={tsCode}
            onChange={(e) => setTsCode(e.target.value)}
            placeholder="ts_code"
            style={{ width: 120 }}
          />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" loading={loading} onClick={() => void load()}>
              查询
            </Button>
          </Space>
        </Form.Item>
      </Form>

      <Tabs
        activeKey={tab}
        onChange={(k) => setTab(k as TableName)}
        items={[
          { key: 'portfolio', label: '持仓' },
          { key: 'trades', label: '成交' },
          { key: 'returns', label: '日收益' },
        ]}
      />

      <ProTable<Record<string, unknown>>
        rowKey={(_, i) => String(i)}
        columns={columns}
        dataSource={table?.rows || []}
        loading={loading}
        search={false}
        pagination={{ pageSize: 50 }}
        toolBarRender={false}
        scroll={{ x: true }}
      />
    </>
  );
}
