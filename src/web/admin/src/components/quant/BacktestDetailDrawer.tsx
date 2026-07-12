import { useMemo } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Empty,
  Row,
  Statistic,
  Table,
  Typography,
} from 'antd';
import { Link } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { BacktestRunItem } from '@/types/quant';

const { Paragraph, Text, Title } = Typography;

function fmtPct(v: number | null | undefined, digits = 2): string {
  if (v == null || Number.isNaN(Number(v))) return '-';
  return `${(Number(v) * 100).toFixed(digits)}%`;
}

function fmtNum(v: number | null | undefined, digits = 4): string {
  if (v == null || Number.isNaN(Number(v))) return '-';
  return Number(v).toFixed(digits);
}

type Props = {
  detail: BacktestRunItem | null;
  onClose: () => void;
};

export default function BacktestDetailDrawer({ detail, onClose }: Props) {
  const chartData = useMemo(() => {
    if (!detail?.nav_curves) return [];
    const map = new Map<
      string,
      {
        trade_date: string;
        long_short?: number;
        top?: number;
        bottom?: number;
        benchmark?: number;
        excess?: number;
      }
    >();
    const put = (
      series: { trade_date: string; value: number }[] | undefined,
      key: 'long_short' | 'top' | 'bottom' | 'benchmark' | 'excess',
    ) => {
      for (const p of series || []) {
        if (!p.trade_date) continue;
        const row = map.get(p.trade_date) ?? { trade_date: p.trade_date };
        row[key] = p.value;
        map.set(p.trade_date, row);
      }
    };
    put(detail.nav_curves.long_short, 'long_short');
    put(detail.nav_curves.top, 'top');
    put(detail.nav_curves.bottom, 'bottom');
    put(detail.nav_curves.benchmark, 'benchmark');
    put(detail.nav_curves.excess, 'excess');
    return Array.from(map.values()).sort((a, b) =>
      a.trade_date.localeCompare(b.trade_date),
    );
  }, [detail]);

  const icData = useMemo(() => {
    return (detail?.ic || [])
      .filter((r) => r.trade_date)
      .map((r) => ({
        trade_date: r.trade_date,
        ic: r.ic,
        rank_ic: r.rank_ic,
      }));
  }, [detail]);

  const groupBarData = useMemo(
    () =>
      (detail?.group_totals || []).map((g) => ({
        group_id: g.group_id,
        total_return: Number(g.total_return),
      })),
    [detail],
  );

  const turnoverData = useMemo(
    () =>
      (detail?.turnover_series || []).map((r) => ({
        trade_date: r.trade_date,
        turnover: Number(r.turnover),
      })),
    [detail],
  );

  const cost = detail?.cost;
  const warnings = detail?.warnings || [];

  return (
    <Drawer
      title={detail ? `回测详情 · ${detail.run_id}` : '回测详情'}
      open={!!detail}
      onClose={onClose}
      width={920}
      destroyOnHidden
      extra={
        detail ? (
          <Link to={`/research/backtest-trades?run_id=${detail.run_id}`}>
            <Button type="link">打开明细表</Button>
          </Link>
        ) : null
      }
    >
      {detail ? (
        <>
          {warnings.length > 0 ? (
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
              message="数据质量告警"
              description={
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {warnings.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              }
            />
          ) : null}

          <Row gutter={12} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card size="small">
                <Statistic title="IC 均值" value={fmtNum(detail.ic_mean)} />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="RankIC 均值"
                  value={fmtNum(detail.rank_ic_mean)}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic title="多空夏普" value={fmtNum(detail.sharpe, 3)} />
              </Card>
            </Col>
            <Col span={6}>
              <Card size="small">
                <Statistic
                  title="多空年化 / MDD"
                  value={`${fmtPct(detail.annual_return)} / ${fmtPct(detail.mdd)}`}
                />
              </Card>
            </Col>
          </Row>

          <Descriptions size="small" column={2} bordered style={{ marginBottom: 16 }}>
            <Descriptions.Item label="状态">{detail.status}</Descriptions.Item>
            <Descriptions.Item label="模式">
              {detail.backtest_mode === 'combo' ? '组合' : '单因子'}
            </Descriptions.Item>
            <Descriptions.Item label="标的">
              {detail.backtest_mode === 'combo'
                ? detail.combo_name || `#${detail.combo_id}`
                : detail.factor_name}
            </Descriptions.Item>
            <Descriptions.Item label="区间">
              {detail.start_date} ~ {detail.end_date}
            </Descriptions.Item>
            <Descriptions.Item label="调仓 / 分组">
              {detail.rebalance} / {detail.groups}
            </Descriptions.Item>
            <Descriptions.Item label="基准">
              {detail.benchmark || '000300.SH'}
            </Descriptions.Item>
            <Descriptions.Item label="成本" span={2}>
              佣金 {fmtNum(cost?.commission_rate, 6)} / 印花税{' '}
              {fmtNum(cost?.stamp_duty_rate, 6)} / 滑点{' '}
              {fmtNum(cost?.slippage_rate, 6)}
            </Descriptions.Item>
            <Descriptions.Item label="输出目录" span={2}>
              <Text code style={{ fontSize: 12 }}>
                {detail.output_dir || '-'}
              </Text>
            </Descriptions.Item>
          </Descriptions>

          {detail.error_message ? (
            <Paragraph type="danger">{detail.error_message}</Paragraph>
          ) : null}

          <Title level={5}>净值曲线（起点=1）</Title>
          <Paragraph type="secondary" style={{ marginTop: -8 }}>
            多空 = 最高分组 − 最低分组；基准为沪深300；超额 = 多空净值 / 基准净值。
          </Paragraph>
          {chartData.length > 0 ? (
            <div style={{ width: '100%', height: 320, marginBottom: 24 }}>
              <ResponsiveContainer>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="trade_date" tick={{ fontSize: 11 }} />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    domain={['auto', 'auto']}
                    tickFormatter={(v) => Number(v).toFixed(2)}
                  />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="long_short"
                    name="多空"
                    stroke="#1677ff"
                    dot={false}
                    strokeWidth={2}
                  />
                  <Line
                    type="monotone"
                    dataKey="benchmark"
                    name="沪深300"
                    stroke="#8c8c8c"
                    dot={false}
                    strokeDasharray="4 4"
                  />
                  <Line
                    type="monotone"
                    dataKey="excess"
                    name="超额"
                    stroke="#13c2c2"
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="top"
                    name="最高组"
                    stroke="#52c41a"
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="bottom"
                    name="最低组"
                    stroke="#ff4d4f"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <Empty
              description="暂无收益序列（失败 run 或尚未写出 returns.parquet）"
              style={{ marginBottom: 24 }}
            />
          )}

          <Title level={5}>分组持有期总收益</Title>
          {groupBarData.length > 0 ? (
            <div style={{ width: '100%', height: 260, marginBottom: 24 }}>
              <ResponsiveContainer>
                <BarChart data={groupBarData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="group_id" tick={{ fontSize: 11 }} />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v) => `${(Number(v) * 100).toFixed(0)}%`}
                  />
                  <Tooltip
                    formatter={(v) => fmtPct(Number(v))}
                  />
                  <Bar dataKey="total_return" name="总收益" fill="#1677ff" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <Empty description="暂无分组收益" style={{ marginBottom: 24 }} />
          )}

          <Title level={5}>调仓日换手</Title>
          {turnoverData.length > 0 ? (
            <div style={{ width: '100%', height: 220, marginBottom: 24 }}>
              <ResponsiveContainer>
                <LineChart data={turnoverData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="trade_date" tick={{ fontSize: 11 }} />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v) => `${(Number(v) * 100).toFixed(0)}%`}
                  />
                  <Tooltip formatter={(v) => fmtPct(Number(v))} />
                  <Line
                    type="monotone"
                    dataKey="turnover"
                    name="换手"
                    stroke="#fa8c16"
                    dot
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <Empty description="暂无换手序列" style={{ marginBottom: 24 }} />
          )}

          <Title level={5}>分年度绩效（多空）</Title>
          <Table
            size="small"
            pagination={false}
            style={{ marginBottom: 24 }}
            rowKey="year"
            dataSource={detail.yearly || []}
            columns={[
              { title: '年', dataIndex: 'year', width: 80 },
              {
                title: '年化',
                dataIndex: 'annual_return',
                render: (v) => fmtPct(v),
              },
              {
                title: '夏普',
                dataIndex: 'sharpe',
                render: (v) => fmtNum(v, 3),
              },
              {
                title: 'MDD',
                dataIndex: 'mdd',
                render: (v) => fmtPct(v),
              },
              { title: '交易日', dataIndex: 'n_days', width: 90 },
            ]}
            locale={{ emptyText: '暂无分年数据' }}
          />

          <Title level={5}>调仓日 IC</Title>
          {icData.length > 0 ? (
            <div style={{ width: '100%', height: 220, marginBottom: 16 }}>
              <ResponsiveContainer>
                <LineChart data={icData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="trade_date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="ic"
                    name="IC"
                    stroke="#722ed1"
                    dot
                  />
                  <Line
                    type="monotone"
                    dataKey="rank_ic"
                    name="RankIC"
                    stroke="#fa8c16"
                    dot
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <Empty description="暂无 IC 序列" style={{ marginBottom: 16 }} />
          )}

          <details>
            <summary style={{ cursor: 'pointer', marginBottom: 8 }}>
              原始 summary JSON
            </summary>
            <pre
              style={{
                background: 'var(--ant-color-fill-quaternary)',
                padding: 12,
                borderRadius: 6,
                overflow: 'auto',
                fontSize: 12,
              }}
            >
              {JSON.stringify(detail.summary ?? {}, null, 2)}
            </pre>
          </details>
        </>
      ) : null}
    </Drawer>
  );
}
