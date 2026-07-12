import type { ReactNode } from 'react';

/**
 * 应用路由 + 菜单 + Tab 的统一配置项。
 *
 * 一份配置同时驱动：
 *  1. React Router 的 RouteObject 树（buildRouterRoutes）
 *  2. 侧边菜单（buildMenuItems）
 *  3. Tab 标签页（通过 path 反查 RouteConfig 拿到 name 等元信息）
 */
export interface RouteConfig {
  /** 完整路径，如 `/demo/page1`；必须全局唯一 */
  path: string;
  /** 菜单名 + Tab 标题（中文） */
  name: string;
  /** 菜单图标 */
  icon?: ReactNode;
  /**
   * 页面组件。叶子节点必填；纯分组（在侧边菜单作为父级容器）可不传，
   * 此时该节点本身不能被路由命中，仅作为菜单分组。
   */
  element?: ReactNode;
  /** 是否在侧边菜单隐藏。默认 false */
  hideInMenu?: boolean;
  /** 是否在 Tab 中可关闭。默认 true，首页等可设为 false */
  closable?: boolean;
  /** 子路由 / 子菜单 */
  children?: RouteConfig[];
}
