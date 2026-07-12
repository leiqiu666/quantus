import { Avatar, Dropdown, Space, Typography } from 'antd';
import { UserOutlined, LogoutOutlined, SettingOutlined } from '@ant-design/icons';

const { Title } = Typography;

/**
 * 顶部导航条：左侧 Logo + 标题，右侧用户菜单。
 * 后续可在此挂消息中心、主题切换、全局搜索等。
 */
export default function HeaderBar() {
  return (
    <div className="flex items-center justify-between h-full px-4">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded bg-blue-600 flex items-center justify-center text-white font-bold">
          Q
        </div>
        <Title level={4} style={{ margin: 0, color: '#fff' }}>
          Quantus Admin
        </Title>
      </div>

      <Space size="middle">
        <Dropdown
          menu={{
            items: [
              {
                key: 'profile',
                icon: <UserOutlined />,
                label: '个人中心',
              },
              {
                key: 'settings',
                icon: <SettingOutlined />,
                label: '账号设置',
              },
              { type: 'divider' },
              {
                key: 'logout',
                icon: <LogoutOutlined />,
                label: '退出登录',
                danger: true,
              },
            ],
          }}
        >
          <Space className="cursor-pointer text-white">
            <Avatar size="small" icon={<UserOutlined />} />
            <span>管理员</span>
          </Space>
        </Dropdown>
      </Space>
    </div>
  );
}
