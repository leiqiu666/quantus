import type { RouteObject } from 'react-router-dom';
import type { MenuProps } from 'antd';
import type { RouteConfig } from '@/types/route';

type MenuItem = NonNullable<MenuProps['items']>[number];

/**
 * 将 RouteConfig 树扁平化为 React Router v7 的 RouteObject[]。
 *
 * 注意：所有 RouteConfig.path 都使用「绝对完整路径」，因此扁平化即可，
 * 不需要再处理嵌套路径拼接。BasicLayout 作为外层容器统一在调用方包裹。
 */
export function buildRouterRoutes(configs: RouteConfig[]): RouteObject[] {
  const routes: RouteObject[] = [];

  const walk = (nodes: RouteConfig[]) => {
    for (const node of nodes) {
      if (node.element) {
        routes.push({
          path: node.path,
          element: node.element,
        });
      }
      if (node.children?.length) {
        walk(node.children);
      }
    }
  };

  walk(configs);
  return routes;
}

/**
 * 将 RouteConfig 树转换为 antd Menu 所需的 items（保留嵌套，形成二级菜单）。
 * 隐藏（hideInMenu）的节点会被过滤掉。
 */
export function buildMenuItems(configs: RouteConfig[]): MenuItem[] {
  return configs
    .filter((c) => !c.hideInMenu)
    .map((c) => {
      const visibleChildren = c.children?.filter((cc) => !cc.hideInMenu) ?? [];
      const item: MenuItem = {
        key: c.path,
        label: c.name,
        icon: c.icon,
        children: visibleChildren.length
          ? buildMenuItems(visibleChildren)
          : undefined,
      };
      return item;
    });
}

/**
 * 根据完整 path 在 RouteConfig 树中查找对应节点。
 * 用于 Tab 反查标题、closable 等元信息。
 */
export function findRouteByPath(
  configs: RouteConfig[],
  path: string,
): RouteConfig | undefined {
  for (const node of configs) {
    if (node.path === path) return node;
    if (node.children?.length) {
      const found = findRouteByPath(node.children, path);
      if (found) return found;
    }
  }
  return undefined;
}

/**
 * 给定一个 path，沿 RouteConfig 树往上找父级节点的 path 列表（不含自身）。
 * 用于侧边菜单展开时确定 openKeys。
 */
export function getAncestorKeys(configs: RouteConfig[], path: string): string[] {
  const result: string[] = [];

  const walk = (nodes: RouteConfig[], trail: string[]): boolean => {
    for (const node of nodes) {
      if (node.path === path) {
        result.push(...trail);
        return true;
      }
      if (node.children?.length) {
        if (walk(node.children, [...trail, node.path])) return true;
      }
    }
    return false;
  };

  walk(configs, []);
  return result;
}
