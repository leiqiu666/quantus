import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  addTab,
  removeTab,
  setActive,
  closeOthers as closeOthersAction,
  closeAll as closeAllAction,
} from '@/store/slices/tabsSlice';
import { findRouteByPath } from '@/routes/helpers';
import { routesConfig } from '@/routes/routes.config';

/**
 * 业务侧统一的 Tab 操作入口。
 *
 * 所有"打开 / 切换 / 关闭"的副作用都会同时改 Redux 状态与浏览器路由，
 * 保证「URL <-> Tab」始终一致。
 *
 * 用法：
 * ```tsx
 * const { tabs, activeKey, open, close, switchTo } = useTabs();
 * <Button onClick={() => open('/demo/page1')}>打开 Demo1</Button>;
 * ```
 */
export function useTabs() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const tabs = useAppSelector((s) => s.tabs.tabs);
  const activeKey = useAppSelector((s) => s.tabs.activeKey);

  /** 通过 path 打开 / 激活一个 Tab；若路由不存在则忽略 */
  const open = useCallback(
    (path: string) => {
      const route = findRouteByPath(routesConfig, path);
      if (!route || !route.element) return;
      dispatch(
        addTab({
          key: route.path,
          label: route.name,
          closable: route.closable !== false,
        }),
      );
      navigate(route.path);
    },
    [dispatch, navigate],
  );

  /** 切换激活的 Tab（同时同步 URL） */
  const switchTo = useCallback(
    (key: string) => {
      dispatch(setActive(key));
      navigate(key);
    },
    [dispatch, navigate],
  );

  /** 关闭一个 Tab；若关闭的是当前激活项，会自动跳到相邻 Tab */
  const close = useCallback(
    (key: string) => {
      const idx = tabs.findIndex((t) => t.key === key);
      if (idx === -1) return;
      const target = tabs[idx];
      if (!target.closable) return;

      dispatch(removeTab(key));

      if (activeKey === key) {
        const next = tabs[idx + 1] ?? tabs[idx - 1];
        if (next) navigate(next.key);
      }
    },
    [tabs, activeKey, dispatch, navigate],
  );

  /** 关闭其他 Tab，仅保留指定 key 与不可关闭项 */
  const closeOthers = useCallback(
    (key: string) => {
      dispatch(closeOthersAction(key));
      navigate(key);
    },
    [dispatch, navigate],
  );

  /** 关闭全部可关闭 Tab；激活第一个保留项 */
  const closeAll = useCallback(() => {
    dispatch(closeAllAction());
    const firstPinned = tabs.find((t) => !t.closable);
    if (firstPinned) navigate(firstPinned.key);
  }, [dispatch, navigate, tabs]);

  return { tabs, activeKey, open, switchTo, close, closeOthers, closeAll };
}
