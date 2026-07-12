import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useAppDispatch } from '@/store/hooks';
import { addTab } from '@/store/slices/tabsSlice';
import { findRouteByPath } from '@/routes/helpers';
import { routesConfig } from '@/routes/routes.config';

/**
 * 监听浏览器路由变化，自动把对应路由作为 Tab 注入 / 激活。
 *
 * 在 BasicLayout 顶层调用一次即可。任何形式的路由切换
 * （点击菜单 / 程序内 navigate / 浏览器前进后退 / 直接输入地址）
 * 都会自动反映到 Tab 栏。
 *
 * 不可路由的节点（如纯菜单分组、`*` 通配中无意义的路径）将被忽略。
 */
export function useSyncTabs() {
  const dispatch = useAppDispatch();
  const { pathname } = useLocation();

  useEffect(() => {
    const route = findRouteByPath(routesConfig, pathname);
    if (!route || !route.element) return;

    dispatch(
      addTab({
        key: route.path,
        label: route.name,
        // closable 默认 true，仅当显式声明 false 时才不可关闭
        closable: route.closable !== false,
      }),
    );
  }, [pathname, dispatch]);
}
