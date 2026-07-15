import { useEffect, useMemo, useState } from 'react';
import {
  Button,
  DatePicker,
  Form,
  Input,
  Select,
  Typography,
  message,
} from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getFactorOptions } from '@/services/quant';
import { getStockKline } from '@/services/research';
import type { FactorMetaItem } from '@/types/quant';

const { Title, Paragraph } = Typography;
const { RangePicker } = DatePicker;

type ChartRow = {
  trade_date: string;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  vol?: number;
  factor?: number;
};

export default function StockKlinePage() {
  const [factors, setFactors] = useState<FactorMetaItem[]>([]);
  const [tsCode, setTsCode] = useState('000001.SZ');
  const [range, setRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(6, 'month'),
    dayjs(),
  ]);
  const [factorName, setFactorName] = useState<string>();
  const [data, setData] = useState<ChartRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void getFactorOptions()
      .then(setFactors)
      .catch(() => undefined);
  }, []);

  const onQuery = async () => {
    if (!tsCode.trim() || !range?.[0] || !range?.[1]) {
      message.warning('请填写代码与区间');
      return;
    }
    setLoading(true);
    try {
      const res = await getStockKline({
        ts_code: tsCode.trim(),
        start: range[0].format('YYYYMMDD'),
        end: range[1].format('YYYYMMDD'),
        factor_name: factorName,
      });
      const fmap = new Map(
        (res.factor || []).map((f) => [f.trade_date, f.value]),
      );
      setData(
        (res.bars || []).map((b) => ({
          trade_date: String(b.trade_date),
          open: b.open == null ? undefined : Number(b.open),
          high: b.high == null ? undefined : Number(b.high),
          low: b.low == null ? undefined : Number(b.low),
          close: b.close == null ? undefined : Number(b.close),
          vol: b.vol == null ? undefined : Number(b.vol),
          factor: fmap.get(String(b.trade_date)),
        })),
      );
    } catch (e) {
      message.error(e instanceof Error ? e.message : '查询失败');
    } finally {
      setLoading(false);
    }
  };

  const factorOptions = useMemo(
    () => factors.map((f) => ({ label: f.factor_name, value: f.factor_name })),
    [factors],
  );

  return (
    <>
      <Title level={4} style={{ marginBottom: 8 }}>
        个股K线
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        日线研究主路径（非分钟实时）。可选叠加因子时间序列（右轴）。
      </Paragraph>

      <Form layout="inline" style={{ marginBottom: 16, rowGap: 12 }}>
        <Form.Item label="代码">
          <Input
            value={tsCode}
            onChange={(e) => setTsCode(e.target.value)}
            style={{ width: 140 }}
            placeholder="000001.SZ"
          />
        </Form.Item>
        <Form.Item label="区间">
          <RangePicker
            value={range}
            onChange={(v) => {
              if (v?.[0] && v?.[1]) setRange([v[0], v[1]]);
            }}
          />
        </Form.Item>
        <Form.Item label="叠加因子">
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            style={{ width: 220 }}
            options={factorOptions}
            value={factorName}
            onChange={setFactorName}
            placeholder="可选"
          />
        </Form.Item>
        <Form.Item>
          <Button type="primary" loading={loading} onClick={() => void onQuery()}>
            查询
          </Button>
        </Form.Item>
      </Form>

      <div style={{ width: '100%', height: 420 }}>
        {data.length > 0 ? (
          <ResponsiveContainer>
            <ComposedChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="trade_date" tick={{ fontSize: 11 }} />
              <YAxis
                yAxisId="price"
                tick={{ fontSize: 11 }}
                domain={['auto', 'auto']}
              />
              <YAxis
                yAxisId="vol"
                orientation="right"
                tick={{ fontSize: 10 }}
                hide={!factorName}
              />
              <Tooltip />
              <Legend />
              <Bar
                yAxisId="price"
                dataKey="vol"
                name="成交量"
                fill="#d9d9d9"
                opacity={0.35}
              />
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="close"
                name="收盘"
                stroke="#1677ff"
                dot={false}
                strokeWidth={2}
              />
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="high"
                name="最高"
                stroke="#52c41a"
                dot={false}
                strokeOpacity={0.5}
              />
              <Line
                yAxisId="price"
                type="monotone"
                dataKey="low"
                name="最低"
                stroke="#ff4d4f"
                dot={false}
                strokeOpacity={0.5}
              />
              {factorName ? (
                <Line
                  yAxisId="vol"
                  type="monotone"
                  dataKey="factor"
                  name={factorName}
                  stroke="#722ed1"
                  dot={false}
                />
              ) : null}
            </ComposedChart>
          </ResponsiveContainer>
        ) : (
          <Paragraph type="secondary">查询后展示日线收盘与成交量</Paragraph>
        )}
      </div>
    </>
  );
}
