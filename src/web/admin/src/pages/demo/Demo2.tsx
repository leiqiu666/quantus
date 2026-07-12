import { Card, Typography, Tag } from 'antd';

const { Title, Paragraph } = Typography;

/**
 * Demo 页面 2。
 *
 * 与 Demo1 配对，用于演示同一菜单分组下的 Tab 切换体验。
 */
export default function Demo2() {
  return (
    <div className="space-y-4">
      <div>
        <Title level={3} style={{ marginBottom: 8 }}>
          Demo 页面 2 <Tag color="green">DEMO</Tag>
        </Title>
        <Paragraph type="secondary">
          点击侧边「Demo / Demo页面2」，或在首页点击对应按钮均可打开本页。
        </Paragraph>
      </div>

      <Card title="说明">
        <Paragraph>当前页面对应路由：<code>/demo/page2</code></Paragraph>
        <Paragraph>
          要新增更多页面，只需在
          <code className="mx-1">src/routes/routes.config.tsx</code>
          追加一条 RouteConfig 即可，菜单 / Tab 会自动接入。
        </Paragraph>
      </Card>
    </div>
  );
}
