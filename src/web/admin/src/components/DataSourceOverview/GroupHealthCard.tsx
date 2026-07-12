import { Card, Progress, Tag, Typography } from 'antd';
import { Link } from 'react-router-dom';
import type { OverviewGroupItem } from '@/types/dataSource';
import {
  formatOverviewDateKey,
  groupStatusColors,
  groupStatusLabels,
} from './formatDateKey';

const { Text } = Typography;

interface GroupHealthCardProps {
  group: OverviewGroupItem;
}

export default function GroupHealthCard({ group }: GroupHealthCardProps) {
  const pct = Math.round(group.complete_rate * 100);
  const worst = group.worst_column;
  const focus = group.latest_gap_date_key;
  const detailTo = focus
    ? `${group.detail_path}?focus=${focus}`
    : group.detail_path;

  return (
    <Card
      size="small"
      title={
        <Link to={detailTo} style={{ color: 'inherit' }}>
          {group.title}
        </Link>
      }
      extra={
        <Tag color={groupStatusColors[group.status]}>
          {groupStatusLabels[group.status]}
        </Tag>
      }
      hoverable
      styles={{ body: { paddingTop: 8 } }}
    >
      <Progress
        percent={pct}
        size="small"
        status={
          group.status === 'healthy'
            ? 'success'
            : group.status === 'warning'
              ? 'normal'
              : 'exception'
        }
      />
      <div className="mt-2 space-y-1 text-sm">
        <Text type="secondary">
          窗口 {group.window_row_count} {group.date_label} · 完整行{' '}
          {group.rows_complete}/{group.window_row_count}
        </Text>
        {group.gap_cell_count > 0 ? (
          <Text type="danger">缺口 {group.gap_cell_count} 格</Text>
        ) : (
          <Text type="success">无缺口</Text>
        )}
        {worst ? (
          <Text type="secondary" className="block">
            最低：{worst.label} {(worst.ratio * 100).toFixed(1)}%
          </Text>
        ) : null}
        {focus ? (
          <Text type="secondary" className="block">
            最近缺口：
            {formatOverviewDateKey(focus, group.date_key_type)}
          </Text>
        ) : null}
      </div>
    </Card>
  );
}
