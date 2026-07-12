import {
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  message,
  Select,
  Space,
  Typography,
} from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  createSchedulerJob,
  getSchedulerCommands,
  getSchedulerJob,
  updateSchedulerJob,
} from '@/services/scheduler';
import type { ScheduleCommandItem, ScheduleKind } from '@/types/scheduler';
import { SCHEDULE_PRESETS, scheduleKindLabels } from '@/types/scheduler';

const { Title } = Typography;

export default function SchedulerJobEditPage() {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editKey = searchParams.get('key');
  const isEdit = Boolean(editKey);

  const [commands, setCommands] = useState<ScheduleCommandItem[]>([]);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getSchedulerCommands().then(setCommands).catch(console.error);
  }, []);

  useEffect(() => {
    if (!editKey) return;
    getSchedulerJob(editKey)
      .then((job) => {
        form.setFieldsValue({
          job_key: job.job_key,
          name: job.name,
          schedule_kind: job.schedule_kind,
          schedule_time: job.schedule_time,
          run_on_trading_day: job.run_on_trading_day,
          enabled: job.enabled,
        });
        setSelectedKeys(job.command_keys);
      })
      .catch(console.error);
  }, [editKey, form]);

  const commandOptions = useMemo(
    () =>
      commands.map((c) => ({
        label: c.label,
        value: c.command_key,
      })),
    [commands],
  );

  const applyPreset = (index: number) => {
    const preset = SCHEDULE_PRESETS[index];
    form.setFieldsValue({
      schedule_kind: preset.kind,
      schedule_time: preset.time,
    });
  };

  const onSubmit = async () => {
    const values = await form.validateFields();
    if (!selectedKeys.length) {
      message.error('请至少选择一个命令');
      return;
    }
    setLoading(true);
    try {
      const payload = {
        ...values,
        command_keys: selectedKeys,
      };
      if (isEdit && editKey) {
        await updateSchedulerJob(editKey, payload);
        message.success('已更新');
      } else {
        await createSchedulerJob(payload);
        message.success('已创建');
      }
      navigate('/scheduler/jobs');
    } catch (e) {
      message.error(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Title level={4} style={{ marginBottom: 16 }}>
        {isEdit ? '编辑调度任务' : '新建调度任务'}
      </Title>
      <Card>
        <Form form={form} layout="vertical" initialValues={{ enabled: true, schedule_kind: 'daily_at', schedule_time: '08:00' }}>
          <Form.Item name="job_key" label="任务键" rules={[{ required: true }]} hidden={isEdit}>
            <Input placeholder="如 pre-market-basic" disabled={isEdit} />
          </Form.Item>
          <Form.Item name="name" label="显示名" rules={[{ required: true }]}>
            <Input placeholder="开盘前基础数据" />
          </Form.Item>
          <Space wrap style={{ marginBottom: 16 }}>
            {SCHEDULE_PRESETS.map((p, i) => (
              <Button key={p.label} onClick={() => applyPreset(i)}>
                {p.label}
              </Button>
            ))}
          </Space>
          <Space>
            <Form.Item name="schedule_kind" label="周期类型" rules={[{ required: true }]}>
              <Select
                style={{ width: 140 }}
                options={(Object.keys(scheduleKindLabels) as ScheduleKind[]).map((k) => ({
                  label: scheduleKindLabels[k],
                  value: k,
                }))}
              />
            </Form.Item>
            <Form.Item name="schedule_time" label="时间 (HH:MM)" rules={[{ required: true, pattern: /^\d{2}:\d{2}$/ }]}>
              <Input style={{ width: 120 }} placeholder="09:25" />
            </Form.Item>
          </Space>
          <Form.Item name="run_on_trading_day" valuePropName="checked">
            <Checkbox>仅 SSE 开市日执行</Checkbox>
          </Form.Item>
          <Form.Item name="enabled" valuePropName="checked">
            <Checkbox>启用</Checkbox>
          </Form.Item>
          <Form.Item label="绑定命令（按选择顺序串行执行）" required>
            <Select
              mode="multiple"
              value={selectedKeys}
              onChange={setSelectedKeys}
              options={commandOptions}
              optionFilterProp="label"
              style={{ width: '100%' }}
              placeholder="选择 ETL 命令"
            />
          </Form.Item>
          <Space>
            <Button type="primary" loading={loading} onClick={onSubmit}>
              保存
            </Button>
            <Button onClick={() => navigate('/scheduler/jobs')}>取消</Button>
          </Space>
        </Form>
      </Card>
    </>
  );
}
