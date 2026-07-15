import { useMemo, useRef, useState } from 'react';
import {
  Button,
  DatePicker,
  Drawer,
  Form,
  Input,
  Modal,
  Space,
  Switch,
  Typography,
  message,
} from 'antd';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import dayjs, { type Dayjs } from 'dayjs';
import {
  getFactorDetail,
  getFactorList,
  getFactorSource,
  updateFactorMeta,
} from '@/services/quant';
import type { FactorMetaItem } from '@/types/quant';
import { useSseTask } from '@/components/SseTask';
import FormulaBuilder from '@/components/quant/formula/FormulaBuilder';
import StartBacktestModal, {
  type BacktestTarget,
} from '@/components/quant/StartBacktestModal';
import { ApiError } from '@/utils/request';

const { Title, Text, Paragraph } = Typography;
const { RangePicker } = DatePicker;
const { TextArea } = Input;

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

const implKindEnum: Record<string, { text: string }> = {
  formula: { text: '公式' },
  python: { text: 'Python' },
  tushare: { text: 'Tushare映射' },
};

export default function FactorList() {
  const actionRef = useRef<ActionType>(null);
  const { startEtlTask, guardEtlTask } = useSseTask();
  const defaultRange = useMemo((): [Dayjs, Dayjs] => {
    const end = dayjs().startOf('month');
    const start = end.subtract(2, 'month');
    return [start, end];
  }, []);
  const [range, setRange] = useState<[Dayjs, Dayjs]>(defaultRange);
  const [btOpen, setBtOpen] = useState(false);
  const [btTarget, setBtTarget] = useState<BacktestTarget | null>(null);

  const [editOpen, setEditOpen] = useState(false);
  const [editing, setEditing] = useState<FactorMetaItem | null>(null);
  const [sourceCode, setSourceCode] = useState<string>('');
  const [sourcePath, setSourcePath] = useState<string>('');
  const [editForm] = Form.useForm<{
    display_name?: string;
    category?: string;
    formula?: string;
  }>();

  const [genOpen, setGenOpen] = useState(false);
  const [genRow, setGenRow] = useState<FactorMetaItem | null>(null);
  const [genRange, setGenRange] = useState<[Dayjs, Dayjs]>(defaultRange);
  const [genForce, setGenForce] = useState(false);

  const onComputeGtja = () => {
    const startDate = range[0].startOf('month').format('YYYYMMDD');
    const endDate = range[1].endOf('month').format('YYYYMMDD');
    const params = {
      taskKey: 'gtja191_compute',
      label: '国泰191计算',
      startDate,
      endDate,
    };
    if (!guardEtlTask(params)) return;
    if (startEtlTask(params)) {
      message.success('已提交国泰191计算任务');
    }
  };

  const openEdit = async (row: FactorMetaItem) => {
    try {
      const detail = await getFactorDetail(row.factor_name);
      setEditing(detail);
      editForm.setFieldsValue({
        display_name: detail.display_name ?? undefined,
        category: detail.category ?? undefined,
        formula: detail.formula ?? undefined,
      });
      setSourceCode('');
      setSourcePath(detail.python_path ?? '');
      if (detail.impl_kind === 'python') {
        try {
          const src = await getFactorSource(detail.factor_name);
          setSourceCode(src.content);
          setSourcePath(src.python_path);
        } catch (e) {
          const msg =
            e instanceof ApiError
              ? String((e.body as { detail?: string })?.detail ?? e.message)
              : e instanceof Error
                ? e.message
                : '加载源码失败';
          setSourceCode(`// ${msg}`);
        }
      }
      setEditOpen(true);
    } catch {
      message.error('加载因子详情失败');
    }
  };

  const onSaveEdit = async () => {
    if (!editing) return;
    const values = await editForm.validateFields();
    try {
      const body: {
        display_name?: string | null;
        category?: string | null;
        formula?: string | null;
      } = {
        display_name: values.display_name ?? null,
        category: values.category ?? null,
      };
      if (editing.impl_kind === 'formula') {
        body.formula = values.formula ?? null;
      }
      await updateFactorMeta(editing.factor_name, body);
      message.success('已保存');
      setEditOpen(false);
      setEditing(null);
      actionRef.current?.reload();
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? String((e.body as { detail?: string })?.detail ?? e.message)
          : '保存失败';
      message.error(msg);
    }
  };

  const openGenerate = (row: FactorMetaItem) => {
    if (row.impl_kind === 'tushare') {
      message.warning('Tushare 因子请使用 Research CLI：tushare-factor pull-by-date-range');
      return;
    }
    setGenRow(row);
    const start = row.start_date ? dayjs(row.start_date, 'YYYYMMDD') : defaultRange[0];
    const end = row.end_date ? dayjs(row.end_date, 'YYYYMMDD') : defaultRange[1];
    setGenRange([
      start.isValid() ? start.startOf('month') : defaultRange[0],
      end.isValid() ? end.startOf('month') : defaultRange[1],
    ]);
    setGenForce(false);
    setGenOpen(true);
  };

  const onGenerate = () => {
    if (!genRow) return;
    const startDate = genRange[0].startOf('month').format('YYYYMMDD');
    const endDate = genRange[1].endOf('month').format('YYYYMMDD');
    const params = {
      taskKey: 'factor_compute',
      label: `因子计算 · ${genRow.factor_name}`,
      startDate,
      endDate,
      factorCompute: {
        factorName: genRow.factor_name,
        force: genForce,
      },
    };
    if (!guardEtlTask(params)) return;
    if (startEtlTask(params)) {
      message.success('已提交因子计算任务');
      setGenOpen(false);
      setGenRow(null);
    }
  };

  const columns: ProColumns<FactorMetaItem>[] = [
    {
      title: '因子名称',
      dataIndex: 'factor_name',
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
      title: '来源',
      dataIndex: 'source',
      width: 90,
      valueEnum: sourceEnum,
    },
    {
      title: '实现',
      dataIndex: 'impl_kind',
      width: 100,
      valueEnum: implKindEnum,
      search: false,
    },
    {
      title: '分类',
      dataIndex: 'category',
      width: 100,
      valueEnum: categoryEnum,
    },
    {
      title: '算法/公式',
      dataIndex: 'formula',
      width: 240,
      search: false,
      ellipsis: true,
    },
    {
      title: '起始日',
      dataIndex: 'start_date',
      width: 100,
      search: false,
    },
    {
      title: '截止日',
      dataIndex: 'end_date',
      width: 100,
      search: false,
    },
    {
      title: '月份数',
      dataIndex: 'month_count',
      width: 80,
      search: false,
    },
    {
      title: '操作',
      width: 180,
      search: false,
      fixed: 'right',
      render: (_, row) => (
        <Space size={0}>
          <Button type="link" size="small" onClick={() => void openEdit(row)}>
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            disabled={row.impl_kind === 'tushare'}
            onClick={() => openGenerate(row)}
          >
            生成
          </Button>
          {row.start_date && row.end_date ? (
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
          ) : null}
        </Space>
      ),
    },
  ];

  return (
    <>
      <Title level={4} style={{ marginBottom: 8 }}>
        因子列表
      </Title>
      <Paragraph type="secondary" style={{ marginBottom: 12 }}>
        权威因子值存于 Parquet <Text code>factor/{'{name}'}/dt=YYYYMM/</Text>。
        公式型可后台改公式；Python 型只读展示源码；行内「生成」按区间写入/覆盖月份分区。
      </Paragraph>
      <Space wrap style={{ marginBottom: 16 }}>
        <Text type="secondary">国泰191整批计算区间（按月）</Text>
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
        actionRef={actionRef}
        columns={columns}
        rowKey="factor_name"
        request={async (params) => {
          const keyword =
            typeof params.factor_name === 'string' ? params.factor_name.trim() : undefined;
          const res = await getFactorList({
            page: params.current ?? 1,
            page_size: params.pageSize ?? 20,
            source: params.source,
            category: params.category,
            keyword: keyword || undefined,
          });
          return { data: res.items, success: true, total: res.total };
        }}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true,
          pageSizeOptions: [20, 50, 100],
        }}
        scroll={{ x: 1300 }}
        search={{ labelWidth: 80 }}
        options={{ density: true, reload: true }}
      />

      <Drawer
        title={editing ? `编辑 · ${editing.factor_name}` : '编辑因子'}
        open={editOpen}
        width={editing?.impl_kind === 'formula' ? 960 : 720}
        onClose={() => {
          setEditOpen(false);
          setEditing(null);
        }}
        extra={
          <Button type="primary" onClick={() => void onSaveEdit()}>
            保存
          </Button>
        }
        destroyOnHidden
      >
        {editing ? (
          <>
            <Paragraph type="secondary">
              实现：{implKindEnum[editing.impl_kind ?? '']?.text ?? editing.impl_kind}
              {sourcePath ? (
                <>
                  <br />
                  路径：<Text code>{sourcePath}</Text>
                </>
              ) : null}
            </Paragraph>
            <Form form={editForm} layout="vertical">
              <Form.Item name="display_name" label="中文名">
                <Input />
              </Form.Item>
              <Form.Item name="category" label="分类">
                <Input />
              </Form.Item>
              {editing.impl_kind === 'formula' ? (
                <Form.Item
                  name="formula"
                  label="公式"
                  extra="点选特征与运算拼装；保存后下次「生成」/国泰计算以本公式为准"
                  trigger="onChange"
                  validateTrigger={[]}
                >
                  <FormulaBuilder />
                </Form.Item>
              ) : null}
              {editing.impl_kind === 'python' ? (
                <Form.Item label="Python 源码（只读）">
                  <TextArea
                    rows={18}
                    value={sourceCode}
                    readOnly
                    style={{ fontFamily: 'ui-monospace, Consolas, monospace', fontSize: 12 }}
                  />
                </Form.Item>
              ) : null}
              {editing.impl_kind === 'tushare' ? (
                <Form.Item name="formula" label="映射说明（只读）">
                  <TextArea rows={6} readOnly />
                </Form.Item>
              ) : null}
            </Form>
            {editing.impl_kind === 'tushare' ? (
              <Text type="secondary">Tushare 因子为字段映射，不可改公式或源码。</Text>
            ) : null}
          </>
        ) : null}
      </Drawer>

      <Modal
        title={genRow ? `生成因子 · ${genRow.factor_name}` : '生成因子'}
        open={genOpen}
        onCancel={() => {
          setGenOpen(false);
          setGenRow(null);
        }}
        onOk={onGenerate}
        okText="开始生成"
        destroyOnHidden
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <Text type="secondary">计算区间（按月）</Text>
            <div style={{ marginTop: 8 }}>
              <RangePicker
                picker="month"
                value={genRange}
                onChange={(v) => {
                  if (v?.[0] && v?.[1]) setGenRange([v[0], v[1]]);
                }}
                style={{ width: '100%' }}
              />
            </div>
          </div>
          <Space>
            <Switch checked={genForce} onChange={setGenForce} />
            <Text>强制覆盖已有月份分区（force）</Text>
          </Space>
        </Space>
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
