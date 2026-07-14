import { Modal, Progress, Typography, Button, Alert } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { useEffect, useRef } from 'react';
import type { SseTask, SseTaskStatus } from '@/store/slices/sseTaskSlice';
import { SUCCESS_AUTO_CLOSE_MS } from './taskFlashConstants';
import { taskFlashClassName } from './taskFlashStyles';

const { Text } = Typography;

interface SseTaskModalProps {
  task: SseTask | null;
  open: boolean;
  onMinimize: () => void;
  onClose: () => void;
  onStop?: () => void;
  allTasks?: SseTask[];
}

function queuePosition(tasks: SseTask[], taskId: string): number {
  const queued = tasks.filter((t) => t.status === 'queued');
  const idx = queued.findIndex((t) => t.id === taskId);
  return idx >= 0 ? idx : 0;
}

function statusLabel(
  task: SseTask,
  allTasks: SseTask[],
): string {
  if (task.mode === 'row_sequence' && task.status === 'running') {
    const stepNo = (task.sequenceStepIndex ?? 0) + 1;
    const total = task.steps?.length ?? task.total;
    const label = task.currentStepLabel ?? '';
    return label
      ? `步骤 ${stepNo}/${total} · ${label}`
      : `步骤 ${stepNo}/${total}`;
  }

  switch (task.status) {
    case 'queued': {
      const ahead = queuePosition(allTasks, task.id);
      return ahead > 0 ? `排队中（前面 ${ahead} 个）` : '排队中';
    }
    case 'pending':
      return '连接中';
    case 'running':
      return '运行中';
    case 'success':
      return task.mode === 'row_sequence' ? '全部步骤已完成' : '已完成';
    case 'error':
      return task.mode === 'row_sequence' && (task.failedStepCount ?? 0) > 0
        ? '任务执行有错误'
        : '失败';
    default:
      return task.status;
  }
}

function StatusIcon({ status }: { status: SseTaskStatus }) {
  switch (status) {
    case 'running':
    case 'pending':
      return <LoadingOutlined className="text-blue-500" />;
    case 'queued':
      return <LoadingOutlined className="text-orange-500" />;
    case 'success':
      return <CheckCircleOutlined className="text-green-500" />;
    case 'error':
      return <CloseCircleOutlined className="text-red-500" />;
    default:
      return null;
  }
}

function modalWrapClass(task: SseTask): string {
  return taskFlashClassName(task, 'sse-task-modal-wrap');
}

export default function SseTaskModal({
  task,
  open,
  onMinimize,
  onClose,
  onStop,
  allTasks = [],
}: SseTaskModalProps) {
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [task?.logs.length]);

  if (!task) {
    return null;
  }

  const isRunning =
    task.status === 'running' ||
    task.status === 'pending' ||
    task.status === 'queued';
  const isSuccessClosing =
    task.flashState === 'success' && task.status === 'success';
  const isError = task.status === 'error' && task.flashState === 'error';
  const isRowSequenceWithErrors =
    task.mode === 'row_sequence' &&
    isError &&
    (task.failedStepCount ?? 0) > 0;
  const progressTotal =
    task.mode === 'row_sequence'
      ? (task.steps?.length ?? task.total)
      : task.total;
  const progressIndex =
    task.mode === 'row_sequence' && isRunning
      ? (task.sequenceStepIndex ?? 0) + 1
      : task.currentIndex;

  const canStop =
    isRunning && task.runId != null && typeof onStop === 'function';

  return (
    <Modal
      title={
        <span className="flex items-center gap-2">
          <StatusIcon status={task.status} />
          {task.name}
        </span>
      }
      open={open}
      onCancel={isSuccessClosing ? undefined : onMinimize}
      width={640}
      mask={false}
      maskClosable={false}
      closable={!isSuccessClosing}
      wrapClassName={modalWrapClass(task)}
      footer={
        isSuccessClosing
          ? [
              <Text key="hint" type="secondary">
                任务成功，{SUCCESS_AUTO_CLOSE_MS / 1000} 秒后自动关闭
              </Text>,
            ]
          : [
              canStop ? (
                <Button key="stop" danger onClick={onStop}>
                  停止
                </Button>
              ) : null,
              <Button key="minimize" onClick={onMinimize}>
                最小化
              </Button>,
              <Button key="close" type="primary" onClick={onClose}>
                关闭
              </Button>,
            ]
      }
    >
      <div className="space-y-4">
        {isError ? (
          <Alert
            type="error"
            showIcon
            message={
              isRowSequenceWithErrors ? '任务执行有错误' : '任务执行失败'
            }
            description={
              isRowSequenceWithErrors
                ? `共 ${task.failedStepCount}/${task.steps?.length ?? task.total} 列失败，其余列已继续执行。请查看下方运行日志了解详情。`
                : '请查看下方运行日志了解详情，修复后可重新发起补位。'
            }
          />
        ) : null}

        <div>
          <div className="flex justify-between mb-1">
            <Text type="secondary">{statusLabel(task, allTasks)}</Text>
            {progressTotal > 0 && (
              <Text type="secondary">
                {progressIndex}/{progressTotal}
              </Text>
            )}
          </div>
          <Progress
            percent={task.progress}
            status={
              task.status === 'error'
                ? 'exception'
                : task.status === 'success'
                  ? 'success'
                  : 'active'
            }
          />
        </div>

        <div>
          <Text strong className="block mb-2">
            运行日志
          </Text>
          <div
            ref={logRef}
            className={`h-64 overflow-y-auto rounded border p-3 font-mono text-xs leading-relaxed ${
              isError
                ? 'border-red-300 bg-red-50'
                : 'border-gray-200 bg-gray-50'
            }`}
          >
            {task.logs.length === 0 ? (
              <Text type="secondary">
                {task.status === 'queued'
                  ? '排队中，等待空闲槽位…'
                  : isRunning
                    ? '等待日志…'
                    : '暂无日志'}
              </Text>
            ) : (
              task.logs.map((line, i) => (
                <div key={`${task.id}-log-${i}`}>{line}</div>
              ))
            )}
          </div>
        </div>
      </div>
    </Modal>
  );
}
