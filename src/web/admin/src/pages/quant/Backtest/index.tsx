import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Button,
  DatePicker,
  Form,
  InputNumber,
  Radio,
  Select,
  Space,
  Typography,
  message,
} from 'antd';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import dayjs, { type Dayjs } from 'dayjs';
import { useSearchParams } from 'react-router-dom';
import { useSseTask } from '@/components/SseTask';
import BacktestDetailDrawer from '@/components/quant/BacktestDetailDrawer';
import {
  getBacktestRun,
  getFactorList,
  listBacktestRuns,
  listFactorCombos,
} from '@/services/quant';
import type { BacktestRunItem, FactorCombo, FactorMetaItem } from '@/types/quant';

const { Title, Paragraph } = Typography;
const { RangePicker } = DatePicker;

export default function BacktestPage() {
  const [searchParams] = useSearchParams();
  const actionRef = useRef<ActionType>(null);
  const { startEtlTask, guardEtlTask } = useSseTask();
  const [factors, setFactors] = useState<FactorMetaItem[]>([]);
  const [combos, setCombos] = useState<FactorCombo[]>([]);
  const [mode, setMode] = useState<'single' | 'combo'>('single');
  const [factorName, setFactorName] = useState<string | undefined>();
  const [comboId, setComboId] = useState<number | undefined>();
  const [groups, setGroups] = useState(10);
  const [rebalance, setRebalance] = useState<'monthly' | 'weekly'>('monthly');
  const [commissionRate, setCommissionRate] = useState(0.0003);
  const [stampDutyRate, setStampDutyRate] = useState(0.001);
  const [slippageRate, setSlippageRate] = useState(0);
  const [range, setRange] = useState<[Dayjs, Dayjs]>(() => [
    dayjs().subtract(3, 'month'),
    dayjs(),
  ]);
  const [detail, setDetail] = useState<BacktestRunItem | null>(null);

  useEffect(() => {
    void Promise.all([getFactorList(), listFactorCombos()])
      .then(([fs, cs]) => {
        setFactors(fs);
        setCombos(cs);
        const q = searchParams.get('factor');
        if (q) {
          setMode('single');
          setFactorName(q);
          const meta = fs.find((f) => f.factor_name === q);
          if (meta?.start_date && meta?.end_date) {
            let start = dayjs(meta.start_date, 'YYYYMMDD');
            const end = dayjs(meta.end_date, 'YYYYMMDD');
            const cap = end.subtract(3, 'year');
            if (start.isBefore(cap)) start = cap;
            setRange([start, end]);
          }
        }
      })
      .catch(() => message.error('加载因子/组合失败'));
  }, [searchParams]);

  const factorOptions = useMemo(
    () =>
      factors
        .filter((f) => f.start_date && f.end_date)
        .map((f) => ({
          label: `${f.factor_name} [${f.start_date}~${f.end_date}]`,
          value: f.factor_name,
        })),
    [factors],
  );

  const onRun = () => {
    if (!range?.[0] || !range?.[1]) {
      message.warning('请选择回测区间');
      return;
    }
    const startDate = range[0].format('YYYYMMDD');
    const endDate = range[1].format('YYYYMMDD');
    if (mode === 'single' && !factorName) {
      message.warning('请选择因子');
      return;
    }
    if (mode === 'combo' && comboId == null) {
      message.warning('请选择组合');
      return;
    }
    const params = {
      taskKey: 'backtest_run',
      label: mode === 'single' ? `回测 ${factorName}` : `回测组合#${comboId}`,
      startDate,
      endDate,
      backtest: {
        backtestMode: mode,
        factorName: mode === 'single' ? factorName : undefined,
        comboId: mode === 'combo' ? comboId : undefined,
        groups,
        rebalance,
        commissionRate,
        stampDutyRate,
        slippageRate,
      },
    };
    if (!guardEtlTask(params)) return;
    if (startEtlTask(params)) {
      message.success('已提交回测任务');
      setTimeout(() => actionRef.current?.reload(), 1500);
    }
  };

  const columns: ProColumns<BacktestRunItem>[] = [
    { title: 'run_id', dataIndex: 'run_id', width: 200, copyable: true },
    {
      title: '模式',
      dataIndex: 'backtest_mode',
      width: 80,
      valueEnum: { single: { text: '单因子' }, combo: { text: '组合' } },
    },
    {
      title: '因子/组合',
      width: 160,
      search: false,
      render: (_, r) =>
        r.backtest_mode === 'combo'
          ? r.combo_name || `#${r.combo_id}`
          : r.factor_name,
    },
    {
      title: '区间',
      width: 180,
      search: false,
      render: (_, r) => `${r.start_date}~${r.end_date}`,
    },
    { title: '状态', dataIndex: 'status', width: 90 },
    {
      title: 'IC',
      dataIndex: 'ic_mean',
      width: 90,
      search: false,
      render: (_, r) =>
        r.ic_mean == null ? '-' : Number(r.ic_mean).toFixed(4),
    },
    {
      title: '夏普',
      dataIndex: 'sharpe',
      width: 90,
      search: false,
      render: (_, r) =>
        r.sharpe == null ? '-' : Number(r.sharpe).toFixed(3),
    },
    { title: '时间', dataIndex: 'created_at', width: 170, search: false },
    {
      title: '操作',
      width: 100,
      search: false,
      render: (_, r) => (
        <Button
          type="link"
          size="small"
          onClick={async () => {
            const d = await getBacktestRun(r.run_id);
            setDetail(d);
          }}
        >
          详情
        </Button>
      ),
    },
  ];

  return (
    <>
      <Title level={4} style={{ marginBottom: 8 }}>
        截面回测
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        回测区间须落在所选因子 Parquet 与日 K 覆盖的交集内。短样本统计仅供冒烟，不可当真评判因子优劣。
      </Paragraph>

      <Form layout="inline" style={{ marginBottom: 16, rowGap: 12 }}>
        <Form.Item label="模式">
          <Radio.Group
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            optionType="button"
            options={[
              { label: '单因子', value: 'single' },
              { label: '组合', value: 'combo' },
            ]}
          />
        </Form.Item>
        {mode === 'single' ? (
          <Form.Item label="因子">
            <Select
              showSearch
              optionFilterProp="label"
              style={{ width: 320 }}
              options={factorOptions}
              value={factorName}
              onChange={setFactorName}
              placeholder="选择因子"
            />
          </Form.Item>
        ) : (
          <Form.Item label="组合">
            <Select
              style={{ width: 240 }}
              options={combos.map((c) => ({
                label: `${c.name}（${c.items.length}）`,
                value: c.id,
              }))}
              value={comboId}
              onChange={setComboId}
              placeholder="选择组合"
            />
          </Form.Item>
        )}
        <Form.Item label="区间">
          <RangePicker
            value={range}
            onChange={(v) => {
              if (v?.[0] && v?.[1]) setRange([v[0], v[1]]);
            }}
          />
        </Form.Item>
        <Form.Item label="调仓">
          <Select
            style={{ width: 120 }}
            value={rebalance}
            onChange={setRebalance}
            options={[
              { label: '月频', value: 'monthly' },
              { label: '周频', value: 'weekly' },
            ]}
          />
        </Form.Item>
        <Form.Item label="分组">
          <InputNumber
            min={2}
            max={20}
            value={groups}
            onChange={(v) => setGroups(Number(v) || 10)}
          />
        </Form.Item>
        <Form.Item label="佣金">
          <InputNumber
            min={0}
            max={0.01}
            step={0.0001}
            value={commissionRate}
            onChange={(v) => setCommissionRate(Number(v) || 0)}
          />
        </Form.Item>
        <Form.Item label="印花税">
          <InputNumber
            min={0}
            max={0.01}
            step={0.0001}
            value={stampDutyRate}
            onChange={(v) => setStampDutyRate(Number(v) || 0)}
          />
        </Form.Item>
        <Form.Item label="滑点">
          <InputNumber
            min={0}
            max={0.01}
            step={0.0001}
            value={slippageRate}
            onChange={(v) => setSlippageRate(Number(v) || 0)}
          />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" onClick={onRun}>
              开始回测
            </Button>
            <Button onClick={() => actionRef.current?.reload()}>刷新历史</Button>
          </Space>
        </Form.Item>
      </Form>

      <ProTable<BacktestRunItem>
        actionRef={actionRef}
        rowKey="run_id"
        columns={columns}
        search={false}
        request={async () => {
          const data = await listBacktestRuns(50);
          return { data, success: true };
        }}
        pagination={{ pageSize: 20 }}
      />

      <BacktestDetailDrawer detail={detail} onClose={() => setDetail(null)} />
    </>
  );
}
