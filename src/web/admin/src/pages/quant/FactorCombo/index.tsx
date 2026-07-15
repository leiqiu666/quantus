import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Button,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Typography,
  message,
} from 'antd';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import {
  createFactorCombo,
  deleteFactorCombo,
  getFactorOptions,
  listFactorCombos,
  updateFactorCombo,
} from '@/services/quant';
import type { FactorCombo, FactorComboItem, FactorMetaItem } from '@/types/quant';
import StartBacktestModal, {
  type BacktestTarget,
} from '@/components/quant/StartBacktestModal';

const { Title, Text } = Typography;

type FormValues = {
  name: string;
  remark?: string;
  items: FactorComboItem[];
};

function comboCoverage(
  combo: FactorCombo,
  factors: FactorMetaItem[],
): { start: string | null; end: string | null } {
  const map = new Map(factors.map((f) => [f.factor_name, f]));
  let start: string | null = null;
  let end: string | null = null;
  for (const it of combo.items || []) {
    const meta = map.get(it.factor_name);
    if (!meta?.start_date || !meta?.end_date) {
      return { start: null, end: null };
    }
    start = start == null || meta.start_date > start ? meta.start_date : start;
    end = end == null || meta.end_date < end ? meta.end_date : end;
  }
  if (start && end && start > end) return { start: null, end: null };
  return { start, end };
}

export default function FactorComboPage() {
  const actionRef = useRef<ActionType>(null);
  const [factors, setFactors] = useState<FactorMetaItem[]>([]);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<FactorCombo | null>(null);
  const [form] = Form.useForm<FormValues>();
  const [btOpen, setBtOpen] = useState(false);
  const [btTarget, setBtTarget] = useState<BacktestTarget | null>(null);

  useEffect(() => {
    void getFactorOptions()
      .then(setFactors)
      .catch(() => {
        message.error('加载因子列表失败');
      });
  }, []);

  const factorOptions = useMemo(
    () =>
      factors
        .filter((f) => f.start_date && f.end_date)
        .map((f) => ({
          label: `${f.factor_name}${f.display_name ? `（${f.display_name}）` : ''}`,
          value: f.factor_name,
        })),
    [factors],
  );

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue({
      name: '',
      remark: '',
      items: [
        { factor_name: undefined as unknown as string, weight: 1 },
        { factor_name: undefined as unknown as string, weight: 1 },
      ],
    });
    setOpen(true);
  };

  const openEdit = (row: FactorCombo) => {
    setEditing(row);
    form.setFieldsValue({
      name: row.name,
      remark: row.remark ?? '',
      items: row.items.map((it) => ({
        factor_name: it.factor_name,
        weight: it.weight,
      })),
    });
    setOpen(true);
  };

  const openBacktest = (row: FactorCombo) => {
    const cov = comboCoverage(row, factors);
    if (!cov.start || !cov.end) {
      message.warning('组合内因子缺少 Parquet 覆盖交集，无法回测');
      return;
    }
    setBtTarget({
      mode: 'combo',
      comboId: row.id,
      comboName: row.name,
      coverStart: cov.start,
      coverEnd: cov.end,
    });
    setBtOpen(true);
  };

  const onSubmit = async () => {
    const values = await form.validateFields();
    const items = (values.items || [])
      .filter((it) => it.factor_name)
      .map((it) => ({
        factor_name: it.factor_name,
        weight: Number(it.weight) || 1,
      }));
    if (items.length < 2) {
      message.warning('至少选择 2 个因子');
      return;
    }
    try {
      if (editing) {
        await updateFactorCombo(editing.id, {
          name: values.name.trim(),
          items,
          remark: values.remark?.trim() || null,
        });
        message.success('已更新');
      } else {
        await createFactorCombo({
          name: values.name.trim(),
          items,
          remark: values.remark?.trim() || null,
        });
        message.success('已创建');
      }
      setOpen(false);
      actionRef.current?.reload();
    } catch (e: unknown) {
      const detail =
        e && typeof e === 'object' && 'body' in e
          ? String((e as { body?: { detail?: string } }).body?.detail ?? e)
          : String(e);
      message.error(detail);
    }
  };

  const columns: ProColumns<FactorCombo>[] = [
    { title: '名称', dataIndex: 'name', width: 180 },
    {
      title: '因子数',
      width: 80,
      search: false,
      render: (_, row) => row.items?.length ?? 0,
    },
    {
      title: '组成',
      search: false,
      ellipsis: true,
      render: (_, row) =>
        (row.items || [])
          .map((it) => `${it.factor_name}×${it.weight}`)
          .join(' + '),
    },
    { title: '备注', dataIndex: 'remark', search: false, ellipsis: true },
    { title: '更新时间', dataIndex: 'updated_at', width: 170, search: false },
    {
      title: '操作',
      width: 200,
      search: false,
      render: (_, row) => (
        <Space>
          <Button type="link" size="small" onClick={() => openBacktest(row)}>
            回测
          </Button>
          <Button type="link" size="small" onClick={() => openEdit(row)}>
            编辑
          </Button>
          <Popconfirm
            title="确认删除该组合？"
            onConfirm={async () => {
              await deleteFactorCombo(row.id);
              message.success('已删除');
              actionRef.current?.reload();
            }}
          >
            <Button type="link" size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Title level={4} style={{ marginBottom: 8 }}>
        因子组合
      </Title>
      <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
        保存命名配方（因子 + 权重），供回测页做截面 z-score 加权合成。不物化 Parquet。
      </Text>
      <ProTable<FactorCombo>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={false}
        toolBarRender={() => [
          <Button key="add" type="primary" onClick={openCreate}>
            新建组合
          </Button>,
        ]}
        request={async () => {
          const data = await listFactorCombos();
          return { data, success: true };
        }}
        pagination={false}
      />
      <Modal
        title={editing ? '编辑组合' : '新建组合'}
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => void onSubmit()}
        width={720}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入名称' }]}
          >
            <Input placeholder="如 gtja_top3" maxLength={100} />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.List name="items">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Space
                    key={field.key}
                    align="baseline"
                    style={{ display: 'flex', marginBottom: 8 }}
                  >
                    <Form.Item
                      {...field}
                      name={[field.name, 'factor_name']}
                      rules={[{ required: true, message: '选因子' }]}
                    >
                      <Select
                        showSearch
                        optionFilterProp="label"
                        style={{ width: 360 }}
                        options={factorOptions}
                        placeholder="因子"
                      />
                    </Form.Item>
                    <Form.Item
                      {...field}
                      name={[field.name, 'weight']}
                      rules={[{ required: true, message: '权重' }]}
                    >
                      <InputNumber min={0.01} step={0.1} style={{ width: 100 }} />
                    </Form.Item>
                    {fields.length > 2 ? (
                      <Button type="link" danger onClick={() => remove(field.name)}>
                        删
                      </Button>
                    ) : null}
                  </Space>
                ))}
                <Button type="dashed" onClick={() => add({ weight: 1 })} block>
                  添加因子
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
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
