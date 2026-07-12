import { createBrowserRouter } from 'react-router-dom';
import BasicLayout from '@/layouts/BasicLayout';
import { routesConfig, fallbackRedirect } from './routes.config';
import { buildRouterRoutes } from './helpers';

/**
 * 应用路由器：
 *  - 顶层用 BasicLayout 包裹，所有页面共用顶部导航 + 侧边菜单 + Tab
 *  - 业务路由通过 buildRouterRoutes 从 routesConfig 自动派生
 */
export const router = createBrowserRouter([
  {
    path: '/',
    element: <BasicLayout />,
    children: [...buildRouterRoutes(routesConfig), fallbackRedirect],
  },
]);
