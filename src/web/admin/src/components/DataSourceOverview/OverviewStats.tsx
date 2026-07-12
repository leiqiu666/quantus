import { Card, Col, Row, Statistic, Typography } from 'antd';
import type { OverviewResponse } from '@/types/dataSource';
import { formatReportPeriod } from '@/utils/report-period';

const { Text } = Typography;

interface OverviewStatsProps {
  data: OverviewResponse | null;
  loading?: boolean;
}

export default function OverviewStats({ data, loading }: OverviewStatsProps) {
  const tradeLabel = data?.latest_trade_date
    ? formatReportPeriod(data.latest_trade_date)
    : '—';
  const tradingHint = data?.is_trading_day ? '今日开市' : '今日休市';

  return (
    <>
      <Row gutter={16}>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic title="数据源总数" value={data?.source_total ?? '—'} suffix="项" />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="分组健康"
              value={data?.groups_healthy ?? '—'}
              suffix={`/ ${data?.group_total ?? 6}`}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic title="待关注缺口" value={data?.gap_cell_count ?? '—'} suffix="格" />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic title="基准日" value={tradeLabel} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {tradingHint}
            </Text>
          </Card>
        </Col>
      </Row>
      {data?.active_stock ? (
        <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
          活跃股数（{formatReportPeriod(data.active_stock.date_key)}）：上市{' '}
          {data.active_stock.listed_count.toLocaleString()} / 可交易{' '}
          {data.active_stock.trading_count.toLocaleString()}
        </Text>
      ) : null}
    </>
  );
}
