import { ReloadOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';

interface HeaderRefreshIconProps {
  title?: string;
  onClick: () => void;
}

export default function HeaderRefreshIcon({
  title = '全量校验并补位',
  onClick,
}: HeaderRefreshIconProps) {
  return (
    <Tooltip title={title}>
      <ReloadOutlined
        className="cursor-pointer text-xs text-gray-400 hover:text-blue-500"
        onClick={(e) => {
          e.stopPropagation();
          onClick();
        }}
      />
    </Tooltip>
  );
}
