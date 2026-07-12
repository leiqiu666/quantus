import { useMemo } from 'react';
import { Menu } from 'antd';
import { useLocation, useNavigate } from 'react-router-dom';
import { buildMenuItems, getAncestorKeys } from '@/routes/helpers';
import { routesConfig } from '@/routes/routes.config';

/**
 * 二级（含多级）侧边菜单，由 routesConfig 自动派生。
 *
 * 选中态：当前路由 path
 * 展开态：当前路由所有祖先节点 path
 */
export default function SideMenu() {
  const location = useLocation();
  const navigate = useNavigate();

  const items = useMemo(() => buildMenuItems(routesConfig), []);
  const openKeys = useMemo(
    () => getAncestorKeys(routesConfig, location.pathname),
    [location.pathname],
  );

  return (
    <Menu
      mode="inline"
      theme="light"
      selectedKeys={[location.pathname]}
      defaultOpenKeys={openKeys}
      items={items}
      onClick={({ key }) => navigate(key)}
      className="!border-r-0"
      style={{ height: '100%' }}
    />
  );
}
