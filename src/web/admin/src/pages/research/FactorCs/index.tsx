import { useEffect, useMemo, useState } from 'react';
import {
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Radio,
  Row,
  Select,
  Statistic,
  Typography,
  message,
} from 'antd';
import type { ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import dayjs, { type Dayjs } from 'dayjs';
import { getFactorOptions, listFactorCombos } from '@/services/quant';
import { getFactorCs } from '@/services/research';
import type { FactorCombo, FactorMetaItem } from '@/types/quant';

const { Title, Paragraph } = Typography;

type Row = { ts_code: string; value: number; rank: number };

export default function FactorCsPage() {
  const [factors, setFactors] = useState<FactorMetaItem[]>([]);
  const [combos, setCombos] = useState<FactorCombo[]>([]);
  const [mode, setMode] = useState<'single' | 'combo'>('single');
  const [factorName, setFactorName] = useState<string>();
  const [comboId, setComboId] = useState<number>();
  const [tradeDate, setTradeDate] = useState<Dayjs>(dayjs());
  const [rows, setRows] = useState<Row[]>([]);
  const [quantiles, setQuantiles] = useState<Record<string, number | null>>({});
  const [loading, setLoading] = useState(false);
  const [label, setLabel] = useState('');

  useEffect(() => {
    void Promise.all([getFactorOptions(), listFactorCombos()])
      .then(([fs, cs]) => {
        setFactors(fs);
        setCombos(cs);
      })
      .catch(() => message.error('加载因子/组合失败'));
  }, []);

  const factorOptions = useMemo(
    () =>
      factors.map((f) => ({
        label: `${f.factor_name}${f.end_date ? ` [${f.end_date}]` : ''}`,
        value: f.factor_name,
      })),
    [factors],
  );

  const onQuery = async () => {
    if (!tradeDate) {
      message.warning('请选择交易日');
      return;
    }
    if (mode === 'single' && !factorName) {
      message.warning('请选择因子');
      return;
    }
    if (mode === 'combo' && comboId == null) {
      message.warning('请选择组合');
      return;
    }
    setLoading(true);
    try {
      const data = await getFactorCs({
        trade_date: tradeDate.format('YYYYMMDD'),
        factor_name: mode === 'single' ? factorName : undefined,
        combo_id: mode === 'combo' ? comboId : undefined,
      });
      setRows(data.rows);
      setQuantiles(data.quantiles || {});
      setLabel(data.factor_name);
    } catch (e) {
      message.error(e instanceof Error ? e.message : '查询失败');
    } finally {
      setLoading(false);
    }
  };

  const columns: ProColumns<Row>[] = [
    { title: '排名', dataIndex: 'rank', width: 80 },
    { title: '代码', dataIndex: 'ts_code', width: 120, copyable: true },
    {
      title: '因子值',
      dataIndex: 'value',
      render: (_, r) => Number(r.value).toFixed(6),
    },
  ];

  return (
    <>
      <Title level={4} style={{ marginBottom: 8 }}>
        因子截面
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        查看单日全市场因子值或组合综合分（z-score 加权）。
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
              style={{ width: 280 }}
              options={factorOptions}
              value={factorName}
              onChange={setFactorName}
              placeholder="选择因子"
            />
          </Form.Item>
        ) : (
          <Form.Item label="组合">
            <Select
              style={{ width: 220 }}
              options={combos.map((c) => ({
                label: c.name,
                value: c.id,
              }))}
              value={comboId}
              onChange={setComboId}
              placeholder="选择组合"
            />
          </Form.Item>
        )}
        <Form.Item label="交易日">
          <DatePicker value={tradeDate} onChange={(d) => d && setTradeDate(d)} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" loading={loading} onClick={() => void onQuery()}>
            查询
          </Button>
        </Form.Item>
      </Form>

      {label ? (
        <Row gutter={12} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic title="标的" value={label} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic title="样本数" value={quantiles.count ?? 0} />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="p10"
                value={
                  quantiles.p10 == null ? '-' : Number(quantiles.p10).toFixed(4)
                }
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="p50"
                value={
                  quantiles.p50 == null ? '-' : Number(quantiles.p50).toFixed(4)
                }
              />
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small">
              <Statistic
                title="p90"
                value={
                  quantiles.p90 == null ? '-' : Number(quantiles.p90).toFixed(4)
                }
              />
            </Card>
          </Col>
        </Row>
      ) : null}

      <ProTable<Row>
        rowKey={(r) => `${r.rank}-${r.ts_code}`}
        columns={columns}
        dataSource={rows}
        search={false}
        loading={loading}
        pagination={{ pageSize: 50 }}
        toolBarRender={false}
      />
    </>
  );
}
