import { Card, Col, Row, Tag, Typography } from 'antd';
import type { OverviewKeyPathItem } from '@/types/dataSource';
import { formatReportPeriod } from '@/utils/report-period';
import {
  keyPathStatusColors,
  keyPathStatusLabels,
} from './formatDateKey';

const { Text, Title } = Typography;

interface KeyPathPanelProps {
  items: OverviewKeyPathItem[];
  referenceDate: string | null;
}

export default function KeyPathPanel({ items, referenceDate }: KeyPathPanelProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div>
      <Title level={5} style={{ marginBottom: 12 }}>
        关键路径滞后
      </Title>
      {referenceDate ? (
        <Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
          参照基准日 {formatReportPeriod(referenceDate)}
        </Text>
      ) : null}
      <Row gutter={[16, 16]}>
        {items.map((item) => (
          <Col xs={24} sm={12} md={8} key={item.name}>
            <Card size="small">
              <div className="flex items-center justify-between">
                <Text strong>{item.name}</Text>
                <Tag color={keyPathStatusColors[item.status]}>
                  {keyPathStatusLabels[item.status]}
                </Tag>
              </div>
              <div className="mt-2 text-sm">
                <Text type="secondary">
                  最新数据：
                  {item.latest_date
                    ? formatReportPeriod(item.latest_date)
                    : '—'}
                </Text>
                {item.lag_days != null ? (
                  <Text type="secondary" className="block">
                    滞后 {item.lag_days} 天
                  </Text>
                ) : null}
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}
