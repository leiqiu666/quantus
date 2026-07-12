import { useMemo, useState } from 'react';
import { Button, DatePicker, Space, Typography, message } from 'antd';
import type { ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import dayjs, { type Dayjs } from 'dayjs';
import { getFactorList } from '@/services/quant';
import type { FactorMetaItem } from '@/types/quant';
import { useSseTask } from '@/components/SseTask';
import StartBacktestModal, {
  type BacktestTarget,
} from '@/components/quant/StartBacktestModal';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const sourceEnum: Record<string, { text: string }> = {
  自研: { text: '自研' },
  tushare: { text: 'Tushare' },
  国泰191: { text: '国泰191' },
};

const categoryEnum: Record<string, { text: string }> = {
  基本面: { text: '基本面' },
  技术: { text: '技术' },
  price_volume: { text: '量价' },
  统计: { text: '统计' },
  gtja191: { text: '国泰191' },
};

export default function FactorList() {
  const { startEtlTask, guardEtlTask } = useSseTask();
  const defaultRange = useMemo((): [Dayjs, Dayjs] => {
    const end = dayjs().startOf('month');
    const start = end.subtract(2, 'month');
    return [start, end];
  }, []);
  const [range, setRange] = useState<[Dayjs, Dayjs]>(defaultRange);
  const [btOpen, setBtOpen] = useState(false);
  const [btTarget, setBtTarget] = useState<BacktestTarget | null>(null);

  const onComputeGtja = () => {
    const startDate = range[0].startOf('month').format('YYYYMMDD');
    const endDate = range[1].endOf('month').format('YYYYMMDD');
    const params = {
      taskKey: 'gtja191_compute',
      label: '国泰191计算',
      startDate,
      endDate,
    };
    if (!guardEtlTask(params)) {
      return;
    }
    if (startEtlTask(params)) {
      message.success('已提交国泰191计算任务');
    }
  };

  const columns: ProColumns<FactorMetaItem>[] = [
    {
      title: '因子名称',
      dataIndex: 'factor_name',
      width: 180,
      search: false,
      fixed: 'left',
    },
    {
      title: '中文名',
      dataIndex: 'display_name',
      width: 200,
      search: false,
      ellipsis: true,
    },
    {
      title: '来源',
      dataIndex: 'source',
      width: 100,
      valueEnum: sourceEnum,
    },
    {
      title: '分类',
      dataIndex: 'category',
      width: 100,
      valueEnum: categoryEnum,
    },
    {
      title: '算法',
      dataIndex: 'formula',
      width: 280,
      search: false,
      ellipsis: true,
    },
    {
      title: '起始日',
      dataIndex: 'start_date',
      width: 110,
      search: false,
    },
    {
      title: '截止日',
      dataIndex: 'end_date',
      width: 110,
      search: false,
    },
    {
      title: '月份数',
      dataIndex: 'month_count',
      width: 90,
      search: false,
      sorter: (a, b) => (a.month_count ?? 0) - (b.month_count ?? 0),
    },
    {
      title: '操作',
      width: 90,
      search: false,
      fixed: 'right',
      render: (_, row) =>
        row.start_date && row.end_date ? (
          <Button
            type="link"
            size="small"
            onClick={() => {
              setBtTarget({
                mode: 'single',
                factorName: row.factor_name,
                coverStart: row.start_date,
                coverEnd: row.end_date,
              });
              setBtOpen(true);
            }}
          >
            回测
          </Button>
        ) : (
          '-'
        ),
    },
  ];

  return (
    <>
      <Title level={4} style={{ marginBottom: 8 }}>
        因子管理
      </Title>
      <Space wrap style={{ marginBottom: 16 }}>
        <Text type="secondary">国泰191计算区间（按月）</Text>
        <RangePicker
          picker="month"
          value={range}
          onChange={(v) => {
            if (v?.[0] && v?.[1]) {
              setRange([v[0], v[1]]);
            }
          }}
        />
        <Button type="primary" onClick={onComputeGtja}>
          计算国泰191
        </Button>
      </Space>
      <ProTable<FactorMetaItem>
        columns={columns}
        rowKey="factor_name"
        request={async (params) => {
          const data = await getFactorList({
            source: params.source,
            category: params.category,
          });
          return { data, success: true, total: data.length };
        }}
        pagination={false}
        scroll={{ x: 1200 }}
        search={{ labelWidth: 80 }}
        options={{ density: true, reload: true }}
      />
      <StartBacktestModal
        open={btOpen}
        target={btTarget}
        onClose={() => {
          setBtOpen(false);
          setBtTarget(null);
        }}
      />
    </>
  );
}
