import { Card, Typography, Tag } from 'antd';

const { Title, Paragraph } = Typography;

/**
 * Demo 页面 1。
 *
 * 仅用于验证「点击菜单 → 路由切换 → Tab 自动新增并激活」的全链路。
 */
export default function Demo1() {
  return (
    <div className="space-y-4">
      <div>
        <Title level={3} style={{ marginBottom: 8 }}>
          Demo 页面 1 <Tag color="blue">DEMO</Tag>
        </Title>
        <Paragraph type="secondary">
          这是一个示例页面，用于演示「路由 + 菜单 + Tab」三位一体能力。
        </Paragraph>
      </div>

      <Card title="说明">
        <Paragraph>当前页面对应路由：<code>/demo/page1</code></Paragraph>
        <Paragraph>它在 routesConfig 中的配置如下：</Paragraph>
        <pre className="bg-gray-50 p-3 rounded text-sm overflow-auto">{`{
  path: '/demo/page1',
  name: 'Demo页面1',
  element: <Demo1 />,
}`}</pre>
        <Paragraph type="secondary" className="!mt-3">
          切换到 Demo 页面 2 后再切回，会发现 Tab 状态被保留。
        </Paragraph>
      </Card>
    </div>
  );
}
