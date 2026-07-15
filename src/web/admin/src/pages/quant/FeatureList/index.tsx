import { useRef, useState } from 'react';
import {
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Switch,
  Typography,
  message,
} from 'antd';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import {
  createFeature,
  getFeatureList,
  refreshFeatureCoverage,
  seedFeatures,
  updateFeature,
} from '@/services/quant';
import type { FeatureMetaItem } from '@/types/quant';
import { ApiError } from '@/utils/request';

const { Title, Text, Paragraph } = Typography;

/** 类型：特征怎么来的 */
const kindOptions = [
  {
    value: 'source',
    label: '源映射',
    title: '直接对应仓库/表里的一列（可加简单变换，如后复权）',
  },
  {
    value: 'derived',
    label: '派生',
    title: '由其它特征或算子计算得到，如 RET、VWAP',
  },
];

/** 数据源：物理从哪读 / 覆盖刷新扫哪类（展示优先写清 Parquet） */
const sourceKindOptions = [
  {
    value: 'kline_daily',
    label: 'Parquet · 个股日K',
    title: '仓库 Parquet：{WAREHOUSE_ROOT}/kline_daily/dt=YYYYMM/',
  },
  {
    value: 'index_daily',
    label: 'Parquet · 指数日K',
    title: '仓库 Parquet：{WAREHOUSE_ROOT}/index_daily/（缺省可回落 PG index_daily）',
  },
  {
    value: 'market_daily_basic',
    label: 'Parquet/PG · 每日指标',
    title: 'market_daily_basic（Parquet 导出或 PG，按落地情况）',
  },
  {
    value: 'derived',
    label: '计算派生（不落盘）',
    title: '不读文件/表列，计算时由引擎生成',
  },
];

const domainOptions = [
  { value: 'stock', label: '个股' },
  { value: 'index', label: '指数' },
];

const frequencyOptions = [
  { value: 'daily', label: '日频' },
];

const kindEnum: Record<string, { text: string }> = Object.fromEntries(
  kindOptions.map((o) => [o.value, { text: o.label }]),
);

const sourceKindEnum: Record<string, { text: string }> = Object.fromEntries(
  sourceKindOptions.map((o) => [o.value, { text: o.label }]),
);

type FeatureForm = {
  feature_name?: string;
  display_name?: string;
  feature_kind: string;
  source_kind: string;
  source_path?: string;
  source_column?: string;
  transform?: string;
  frequency: string;
  domain: string;
  dtype: string;
  formula?: string;
  enabled: boolean;
  sort_order?: number;
  remark?: string;
};

const defaultForm: FeatureForm = {
  feature_kind: 'source',
  source_kind: 'kline_daily',
  source_path: 'parquet:kline_daily',
  frequency: 'daily',
  domain: 'stock',
  dtype: 'float64',
  enabled: true,
  sort_order: 0,
};

export default function FeatureList() {
  const actionRef = useRef<ActionType>(null);
  const [seeding, setSeeding] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<FeatureMetaItem | null>(null);
  const [form] = Form.useForm<FeatureForm>();
  const featureKind = Form.useWatch('feature_kind', form);

  const onSeed = async () => {
    setSeeding(true);
    try {
      const res = await seedFeatures();
      message.success(`已写入 ${res.upserted} 条特征种子`);
      actionRef.current?.reload();
    } catch {
      message.error('初始化种子失败');
    } finally {
      setSeeding(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await refreshFeatureCoverage();
      message.success(
        `已更新 ${res.updated} 条覆盖：K线 ${res.kline_start ?? '-'}~${res.kline_end ?? '-'}`,
      );
      actionRef.current?.reload();
    } catch {
      message.error('刷新覆盖失败');
    } finally {
      setRefreshing(false);
    }
  };

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue({ ...defaultForm, feature_name: undefined, display_name: undefined });
    setEditOpen(true);
  };

  const openEdit = (row: FeatureMetaItem) => {
    setEditing(row);
    form.setFieldsValue({
      feature_name: row.feature_name,
      display_name: row.display_name ?? undefined,
      feature_kind: row.feature_kind,
      source_kind: row.source_kind,
      source_path: row.source_path ?? undefined,
      source_column: row.source_column ?? undefined,
      transform: row.transform ?? undefined,
      frequency: row.frequency,
      domain: row.domain,
      dtype: row.dtype,
      formula: row.formula ?? undefined,
      enabled: row.enabled === 1,
      sort_order: row.sort_order,
      remark: row.remark ?? undefined,
    });
    setEditOpen(true);
  };

  const onSave = async () => {
    const values = await form.validateFields();
    const body = {
      display_name: values.display_name ?? null,
      feature_kind: values.feature_kind,
      source_kind: values.source_kind,
      source_path: values.source_path ?? null,
      source_column: values.source_column ?? null,
      transform: values.transform ?? null,
      frequency: values.frequency,
      domain: values.domain,
      dtype: values.dtype,
      formula: values.formula ?? null,
      enabled: values.enabled ? 1 : 0,
      sort_order: values.sort_order ?? 0,
      remark: values.remark ?? null,
    };
    try {
      if (editing) {
        await updateFeature(editing.id, body);
        message.success('已保存');
      } else {
        await createFeature({
          ...body,
          feature_name: (values.feature_name || '').trim(),
        });
        message.success('已创建');
      }
      setEditOpen(false);
      setEditing(null);
      actionRef.current?.reload();
    } catch (e) {
      let msg = '保存失败';
      if (e instanceof ApiError) {
        const body = e.body as { detail?: unknown } | undefined;
        msg = body?.detail != null ? String(body.detail) : e.message;
      } else if (e instanceof Error) {
        msg = e.message;
      }
      message.error(msg);
    }
  };

  const columns: ProColumns<FeatureMetaItem>[] = [
    {
      title: '符号',
      dataIndex: 'feature_name',
      width: 160,
      fixed: 'left',
      fieldProps: { placeholder: '关键字' },
    },
    {
      title: '中文名',
      dataIndex: 'display_name',
      width: 160,
      search: false,
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'feature_kind',
      width: 100,
      valueEnum: kindEnum,
      tooltip: '源映射=直接读列；派生=由其它特征计算',
    },
    {
      title: '数据源',
      dataIndex: 'source_kind',
      width: 150,
      valueEnum: sourceKindEnum,
      tooltip: '权威存储形态优先写 Parquet，再写业务类别',
    },
    {
      title: '源路径',
      dataIndex: 'source_path',
      width: 160,
      search: false,
      ellipsis: true,
      tooltip: '如 parquet:kline_daily → WAREHOUSE_ROOT/kline_daily/',
    },
    {
      title: '源列',
      dataIndex: 'source_column',
      width: 100,
      search: false,
    },
    {
      title: '变换',
      dataIndex: 'transform',
      width: 220,
      search: false,
      ellipsis: true,
    },
    {
      title: '频率',
      dataIndex: 'frequency',
      width: 80,
      search: false,
    },
    {
      title: '域',
      dataIndex: 'domain',
      width: 80,
      search: false,
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
      title: '启用',
      dataIndex: 'enabled',
      width: 80,
      valueEnum: {
        1: { text: '是' },
        0: { text: '否' },
      },
    },
    {
      title: '操作',
      width: 80,
      search: false,
      fixed: 'right',
      render: (_, row) => (
        <Button type="link" size="small" onClick={() => openEdit(row)}>
          编辑
        </Button>
      ),
    },
  ];

  return (
    <>
      <Title level={4} style={{ marginBottom: 8 }}>
        特征管理
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 12 }}>
        登记公式里能用的符号及其血缘（不存特征值）。量价权威源是仓库{' '}
        <Text code>Parquet</Text>（如 <Text code>kline_daily/dt=YYYYMM/</Text>
        ），不是 PG 热表。
        <br />
        <b>类型</b>：源映射 = 直接读列；派生 = 由其它特征算出（如 RET）。
        <br />
        <b>数据源</b>：展示为「Parquet · 类别」；「刷新覆盖」按类别扫描对应分区。
      </Paragraph>
      <Space wrap style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={openCreate}>
          新建特征
        </Button>
        <Button loading={seeding} onClick={() => void onSeed()}>
          初始化种子
        </Button>
        <Button loading={refreshing} onClick={() => void onRefresh()}>
          刷新覆盖
        </Button>
      </Space>
      <ProTable<FeatureMetaItem>
        actionRef={actionRef}
        columns={columns}
        rowKey="id"
        request={async (params) => {
          const keyword =
            typeof params.feature_name === 'string'
              ? params.feature_name.trim()
              : undefined;
          const enabledRaw = params.enabled;
          const enabled =
            enabledRaw === 0 || enabledRaw === 1 || enabledRaw === '0' || enabledRaw === '1'
              ? Number(enabledRaw)
              : undefined;
          const res = await getFeatureList({
            page: params.current ?? 1,
            page_size: params.pageSize ?? 20,
            keyword: keyword || undefined,
            feature_kind: params.feature_kind,
            source_kind: params.source_kind,
            enabled,
          });
          return { data: res.items, success: true, total: res.total };
        }}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
          pageSizeOptions: [20, 50, 100],
        }}
        scroll={{ x: 1400 }}
        search={{ labelWidth: 80 }}
        options={{ density: true, reload: true }}
        toolBarRender={false}
      />
      <Modal
        title={editing ? `编辑特征 · ${editing.feature_name}` : '新建特征'}
        open={editOpen}
        onCancel={() => {
          setEditOpen(false);
          setEditing(null);
        }}
        onOk={() => void onSave()}
        width={640}
        destroyOnHidden
      >
        <Form form={form} layout="vertical" initialValues={defaultForm}>
          <Form.Item
            name="feature_name"
            label="符号（公式里用的名字）"
            rules={[{ required: true, message: '必填，如 CLOSE / RET' }]}
            extra={editing ? '创建后不可改符号' : '全局唯一，建议大写'}
          >
            <Input disabled={!!editing} placeholder="CLOSE" />
          </Form.Item>
          <Form.Item name="display_name" label="中文名">
            <Input placeholder="收盘价（后复权）" />
          </Form.Item>
          <Space style={{ display: 'flex' }} size="middle" wrap>
            <Form.Item
              name="feature_kind"
              label="类型"
              rules={[{ required: true }]}
              style={{ minWidth: 200, flex: 1 }}
              tooltip="源映射=直接读列；派生=由其它特征计算"
            >
              <Select options={kindOptions} optionLabelProp="label" />
            </Form.Item>
            <Form.Item
              name="source_kind"
              label="数据源"
              rules={[{ required: true }]}
              style={{ minWidth: 200, flex: 1 }}
              tooltip="物理数据类别（列表展示为 Parquet · …）；刷新覆盖按此扫描"
            >
              <Select options={sourceKindOptions} optionLabelProp="label" />
            </Form.Item>
          </Space>
          <Space style={{ display: 'flex' }} size="middle" wrap>
            <Form.Item name="domain" label="域" style={{ minWidth: 140, flex: 1 }}>
              <Select options={domainOptions} />
            </Form.Item>
            <Form.Item name="frequency" label="频率" style={{ minWidth: 140, flex: 1 }}>
              <Select options={frequencyOptions} />
            </Form.Item>
            <Form.Item name="dtype" label="数据类型" style={{ minWidth: 140, flex: 1 }}>
              <Select
                options={[
                  { value: 'float64', label: 'float64' },
                  { value: 'int64', label: 'int64' },
                  { value: 'string', label: 'string' },
                ]}
              />
            </Form.Item>
          </Space>
          <Space style={{ display: 'flex' }} size="middle" wrap>
            <Form.Item
              name="source_path"
              label="源路径（Parquet 目录或表名）"
              style={{ minWidth: 200, flex: 1 }}
              extra="推荐：parquet:kline_daily"
            >
              <Input placeholder="parquet:kline_daily" />
            </Form.Item>
            <Form.Item
              name="source_column"
              label="源列"
              style={{ minWidth: 200, flex: 1 }}
              extra={featureKind === 'derived' ? '派生特征可留空' : '如 close / vol'}
            >
              <Input placeholder="close" />
            </Form.Item>
          </Space>
          <Form.Item name="transform" label="变换说明">
            <Input.TextArea rows={2} placeholder="close * fill_null(adj_factor, 1.0) → close_adj" />
          </Form.Item>
          <Form.Item
            name="formula"
            label="派生公式"
            extra={featureKind === 'source' ? '源映射一般不需要公式' : '如 CLOSE / DELAY(CLOSE,1) - 1'}
          >
            <Input.TextArea rows={2} placeholder="CLOSE / DELAY(CLOSE,1) - 1" />
          </Form.Item>
          <Space style={{ display: 'flex' }} size="middle" wrap>
            <Form.Item name="sort_order" label="排序" style={{ minWidth: 120 }}>
              <InputNumber style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name="enabled"
              label="启用"
              valuePropName="checked"
              style={{ minWidth: 120 }}
            >
              <Switch />
            </Form.Item>
          </Space>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
