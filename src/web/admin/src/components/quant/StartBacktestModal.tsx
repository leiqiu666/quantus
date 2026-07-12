import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  DatePicker,
  Form,
  InputNumber,
  Modal,
  Select,
  Typography,
  message,
} from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useSseTask } from '@/components/SseTask';

const { Text } = Typography;
const { RangePicker } = DatePicker;

export type BacktestTarget =
  | {
      mode: 'single';
      factorName: string;
      coverStart?: string | null;
      coverEnd?: string | null;
    }
  | {
      mode: 'combo';
      comboId: number;
      comboName: string;
      coverStart?: string | null;
      coverEnd?: string | null;
    };

type Props = {
  open: boolean;
  target: BacktestTarget | null;
  onClose: () => void;
  onSubmitted?: () => void;
};

/** 覆盖区间默认：整段可用；超过约 3 年则默认取最近 3 年。 */
export function defaultBacktestRange(
  coverStart?: string | null,
  coverEnd?: string | null,
): [Dayjs, Dayjs] | null {
  if (!coverStart || !coverEnd || coverStart.length < 8 || coverEnd.length < 8) {
    return null;
  }
  let start = dayjs(coverStart, 'YYYYMMDD');
  let end = dayjs(coverEnd, 'YYYYMMDD');
  if (!start.isValid() || !end.isValid() || start.isAfter(end)) {
    return null;
  }
  const threeYearsAgo = end.subtract(3, 'year');
  if (start.isBefore(threeYearsAgo)) {
    start = threeYearsAgo;
  }
  return [start, end];
}

/**
 * 行内「回测」弹窗。
 * 参数：区间 / 调仓 / 分组 / 成本三项。
 */
export default function StartBacktestModal({
  open,
  target,
  onClose,
  onSubmitted,
}: Props) {
  const { startEtlTask, guardEtlTask } = useSseTask();
  const [range, setRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(3, 'month'),
    dayjs(),
  ]);
  const [rebalance, setRebalance] = useState<'monthly' | 'weekly'>('monthly');
  const [groups, setGroups] = useState(10);
  const [commissionRate, setCommissionRate] = useState(0.0003);
  const [stampDutyRate, setStampDutyRate] = useState(0.001);
  const [slippageRate, setSlippageRate] = useState(0);

  useEffect(() => {
    if (!open || !target) return;
    const r = defaultBacktestRange(target.coverStart, target.coverEnd);
    if (r) setRange(r);
    setRebalance('monthly');
    setGroups(10);
    setCommissionRate(0.0003);
    setStampDutyRate(0.001);
    setSlippageRate(0);
  }, [open, target]);

  const coverText = useMemo(() => {
    if (target?.coverStart && target?.coverEnd) {
      return `${target.coverStart} ~ ${target.coverEnd}`;
    }
    return '未知（请确认 Parquet 已计算）';
  }, [target]);

  const title =
    target?.mode === 'combo'
      ? `回测组合 · ${target.comboName}`
      : target
        ? `回测因子 · ${target.factorName}`
        : '发起回测';

  const onOk = () => {
    if (!target) return;
    if (!range?.[0] || !range?.[1]) {
      message.warning('请选择回测区间');
      return;
    }
    const startDate = range[0].format('YYYYMMDD');
    const endDate = range[1].format('YYYYMMDD');
    if (target.coverStart && startDate < target.coverStart) {
      message.warning(`起始日早于覆盖 ${target.coverStart}`);
      return;
    }
    if (target.coverEnd && endDate > target.coverEnd) {
      message.warning(`结束日晚于覆盖 ${target.coverEnd}`);
      return;
    }

    const params = {
      taskKey: 'backtest_run',
      label:
        target.mode === 'combo'
          ? `回测 ${target.comboName}`
          : `回测 ${target.factorName}`,
      startDate,
      endDate,
      backtest: {
        backtestMode: target.mode,
        factorName: target.mode === 'single' ? target.factorName : undefined,
        comboId: target.mode === 'combo' ? target.comboId : undefined,
        groups,
        rebalance,
        commissionRate,
        stampDutyRate,
        slippageRate,
      },
    };
    if (!guardEtlTask(params)) return;
    if (startEtlTask(params)) {
      message.success('已提交回测，可在「回测」页查看历史与曲线');
      onSubmitted?.();
      onClose();
    }
  };

  return (
    <Modal
      title={title}
      open={open}
      onCancel={onClose}
      onOk={onOk}
      okText="开始回测"
      destroyOnHidden
      width={560}
    >
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="截面分组回测"
        description="基准固定沪深300。调仓日按因子（或组合综合分）排序分成 N 组，组内等权；输出多空与 IC。"
      />
      <Form layout="vertical">
        <Form.Item label="数据覆盖（只读）">
          <Text code>{coverText}</Text>
        </Form.Item>
        <Form.Item
          label="回测区间"
          required
          extra="默认取覆盖区间；覆盖超过约 3 年时默认最近 3 年。"
        >
          <RangePicker
            value={range}
            onChange={(v) => {
              if (v?.[0] && v?.[1]) setRange([v[0], v[1]]);
            }}
            style={{ width: '100%' }}
          />
        </Form.Item>
        <Form.Item label="调仓频率" extra="月频更稳；周频更敏感、换手更高。">
          <Select
            value={rebalance}
            onChange={setRebalance}
            options={[
              { label: '月频（默认）', value: 'monthly' },
              { label: '周频', value: 'weekly' },
            ]}
          />
        </Form.Item>
        <Form.Item label="分组数" extra="常用 5 或 10；10=十分位，最高组最强。">
          <InputNumber
            min={2}
            max={20}
            value={groups}
            onChange={(v) => setGroups(Number(v) || 10)}
            style={{ width: '100%' }}
          />
        </Form.Item>
        <Form.Item label="佣金费率" extra="默认万三双边。">
          <InputNumber
            min={0}
            max={0.01}
            step={0.0001}
            value={commissionRate}
            onChange={(v) => setCommissionRate(Number(v) || 0)}
            style={{ width: '100%' }}
          />
        </Form.Item>
        <Form.Item label="印花税（卖出）" extra="默认千一。">
          <InputNumber
            min={0}
            max={0.01}
            step={0.0001}
            value={stampDutyRate}
            onChange={(v) => setStampDutyRate(Number(v) || 0)}
            style={{ width: '100%' }}
          />
        </Form.Item>
        <Form.Item label="滑点费率" extra="默认 0。">
          <InputNumber
            min={0}
            max={0.01}
            step={0.0001}
            value={slippageRate}
            onChange={(v) => setSlippageRate(Number(v) || 0)}
            style={{ width: '100%' }}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}
