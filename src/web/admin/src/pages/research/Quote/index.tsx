import { useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Form,
  Input,
  Row,
  Space,
  Statistic,
  Typography,
  message,
} from 'antd';
import { getQuote } from '@/services/research';
import type { QuoteResponse } from '@/types/quant';

const { Title, Paragraph, Text } = Typography;

const WATCH_KEY = 'quantus_research_watchlist';

function loadWatch(): string[] {
  try {
    const raw = localStorage.getItem(WATCH_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr.map(String) : [];
  } catch {
    return [];
  }
}

function saveWatch(codes: string[]) {
  localStorage.setItem(WATCH_KEY, JSON.stringify(codes.slice(0, 20)));
}

function fmtPct(v: number | null | undefined): string {
  if (v == null || Number.isNaN(Number(v))) return '-';
  return `${(Number(v) * 100).toFixed(2)}%`;
}

export default function QuotePage() {
  const [tsCode, setTsCode] = useState('000001.SZ');
  const [quote, setQuote] = useState<QuoteResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [watch, setWatch] = useState<string[]>(() => loadWatch());

  const onQuery = async (code?: string) => {
    const c = (code || tsCode).trim();
    if (!c) {
      message.warning('请输入代码');
      return;
    }
    setTsCode(c);
    setLoading(true);
    try {
      const data = await getQuote(c);
      setQuote(data);
    } catch (e) {
      message.error(e instanceof Error ? e.message : '查询失败');
      setQuote(null);
    } finally {
      setLoading(false);
    }
  };

  const addWatch = () => {
    const c = tsCode.trim();
    if (!c) return;
    if (watch.includes(c)) return;
    const next = [c, ...watch];
    setWatch(next);
    saveWatch(next);
  };

  const removeWatch = (c: string) => {
    const next = watch.filter((x) => x !== c);
    setWatch(next);
    saveWatch(next);
  };

  const changeColor = useMemo(() => {
    if (quote?.change_pct == null) return undefined;
    return quote.change_pct >= 0 ? '#cf1322' : '#3f8600';
  }, [quote]);

  return (
    <>
      <Title level={4} style={{ marginBottom: 8 }}>
        行情快照
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 16 }}>
        TDX 开启时取盘中快照；否则展示最近有日 K 的交易日收盘（非实时）。自选仅存本机。
      </Paragraph>

      <Form layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item label="代码">
          <Input
            value={tsCode}
            onChange={(e) => setTsCode(e.target.value)}
            style={{ width: 140 }}
            onPressEnter={() => void onQuery()}
          />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" loading={loading} onClick={() => void onQuery()}>
              查询
            </Button>
            <Button onClick={addWatch}>加入自选</Button>
          </Space>
        </Form.Item>
      </Form>

      {watch.length > 0 ? (
        <Paragraph>
          自选：{' '}
          {watch.map((c) => (
            <Text key={c} style={{ marginRight: 12 }}>
              <a onClick={() => void onQuery(c)}>{c}</a>{' '}
              <a onClick={() => removeWatch(c)} style={{ color: '#999' }}>
                ×
              </a>
            </Text>
          ))}
        </Paragraph>
      ) : null}

      {quote?.message ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message={quote.message}
        />
      ) : null}

      {quote ? (
        <Row gutter={12}>
          <Col span={6}>
            <Card size="small">
              <Statistic title="模式" value={quote.mode === 'tdx' ? 'TDX' : '日线'} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="代码" value={quote.ts_code} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="交易日" value={quote.trade_date || '-'} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic
                title="现价 / 涨跌"
                value={`${quote.price ?? '-'} / ${fmtPct(quote.change_pct)}`}
                valueStyle={{ color: changeColor }}
              />
            </Card>
          </Col>
          <Col span={6} style={{ marginTop: 12 }}>
            <Card size="small">
              <Statistic title="昨收" value={quote.pre_close ?? '-'} />
            </Card>
          </Col>
          <Col span={6} style={{ marginTop: 12 }}>
            <Card size="small">
              <Statistic title="开" value={quote.open ?? '-'} />
            </Card>
          </Col>
          <Col span={6} style={{ marginTop: 12 }}>
            <Card size="small">
              <Statistic title="高" value={quote.high ?? '-'} />
            </Card>
          </Col>
          <Col span={6} style={{ marginTop: 12 }}>
            <Card size="small">
              <Statistic title="低" value={quote.low ?? '-'} />
            </Card>
          </Col>
        </Row>
      ) : null}
    </>
  );
}
