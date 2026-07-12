import { Card, Typography, Button, Space, Statistic, Row, Col } from 'antd';
import { PlayCircleOutlined, AppstoreOutlined } from '@ant-design/icons';
import { useTabs } from '@/hooks/useTabs';

const { Title, Paragraph } = Typography;

/**
 * 首页：欢迎信息 + 入口按钮。
 *
 * 演示「按钮触发 useTabs.open」也能像点击菜单一样新建/激活 Tab。
 */
export default function Home() {
  const { open } = useTabs();

  return (
    <div className="space-y-6">
      <div>
        <Title level={3} style={{ marginBottom: 8 }}>
          欢迎使用 Quantus Admin
        </Title>
        <Paragraph type="secondary">
          量化 Agent 管理后台 · 用于配置策略、监控运行、回测分析。
        </Paragraph>
      </div>

      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic title="在线 Agent" value={12} suffix="个" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="今日策略调用" value={3489} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="本月盈亏" value={12.34} precision={2} suffix="%" />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="告警数" value={2} valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
      </Row>

      <Card title="快捷入口" size="small">
        <Space>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => open('/demo/page1')}
          >
            打开 Demo页面1
          </Button>
          <Button
            icon={<AppstoreOutlined />}
            onClick={() => open('/demo/page2')}
          >
            打开 Demo页面2
          </Button>
        </Space>
      </Card>
    </div>
  );
}
