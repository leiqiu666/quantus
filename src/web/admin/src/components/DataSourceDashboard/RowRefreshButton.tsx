import { ReloadOutlined } from '@ant-design/icons';
import { Button, Tooltip } from 'antd';

interface RowRefreshButtonProps {
  title?: string;
  onClick: () => void;
}

export default function RowRefreshButton({
  title = '补位本行全部数据源',
  onClick,
}: RowRefreshButtonProps) {
  return (
    <Tooltip title={title}>
      <Button
        type="default"
        size="small"
        icon={<ReloadOutlined style={{ fontSize: 10 }} />}
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
        style={{ width: 22, height: 22, padding: 0, minWidth: 22 }}
      />
    </Tooltip>
  );
}
