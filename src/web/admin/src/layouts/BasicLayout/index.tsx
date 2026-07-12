import { useState } from 'react';
import { Layout } from 'antd';
import { Outlet } from 'react-router-dom';
import HeaderBar from './HeaderBar';
import SideMenu from './SideMenu';
import PageTabs from './PageTabs';
import { useSyncTabs } from '@/hooks/useSyncTabs';
import { SseTaskManager } from '@/components/SseTask';

const { Header, Sider, Content } = Layout;

/**
 * 基础布局：顶部导航 + 二级侧边菜单 + Tab 标签页 + 内容区（Outlet）。
 *
 * 通过 `useSyncTabs()` 让任意路由变化（菜单点击、按钮跳转、浏览器前进后退、
 * 直接输入 URL）都自动同步到 Tab 栏，业务页面无感知。
 */
export default function BasicLayout() {
  const [collapsed, setCollapsed] = useState(false);
  useSyncTabs();

  return (
    <Layout className="h-screen">
      <Header
        className="!px-0 !h-14 !leading-[56px]"
        style={{ background: '#001529' }}
      >
        <HeaderBar />
      </Header>

      <Layout>
        <Sider
          collapsible
          collapsed={collapsed}
          onCollapse={setCollapsed}
          theme="light"
          width={220}
          className="!bg-white shadow-sm"
        >
          <SideMenu />
        </Sider>

        <Layout className="bg-gray-50">
          <PageTabs />
          <Content className="p-4 overflow-auto">
            <div className="bg-white rounded-md shadow-sm p-6 min-h-full">
              <Outlet />
            </div>
          </Content>
        </Layout>
      </Layout>
      <SseTaskManager />
    </Layout>
  );
}
