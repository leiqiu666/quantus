import { Card, Progress, Typography } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  CloseOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import type { SseTask } from '@/store/slices/sseTaskSlice';
import { SUCCESS_AUTO_CLOSE_MS } from './taskFlashConstants';
import { taskFlashClassName } from './taskFlashStyles';

const { Text } = Typography;

interface SseTaskDockProps {
  tasks: SseTask[];
  onRestore: (id: string) => void;
  onClose: (id: string) => void;
  onStop?: (id: string) => void;
}

function DockStatusIcon({ task }: { task: SseTask }) {
  switch (task.status) {
    case 'running':
    case 'pending':
      return <LoadingOutlined className="text-blue-500 shrink-0" />;
    case 'queued':
      return <LoadingOutlined className="text-orange-500 shrink-0" />;
    case 'success':
      return <CheckCircleOutlined className="text-green-500 shrink-0" />;
    case 'error':
      return <CloseCircleOutlined className="text-red-500 shrink-0" />;
    default:
      return null;
  }
}

function dockSubtitle(task: SseTask): string | null {
  if (task.status === 'queued') {
    return '排队中';
  }
  if (
    task.status === 'success' &&
    task.flashState === 'success' &&
    !task.slidingOut
  ) {
    return `${SUCCESS_AUTO_CLOSE_MS / 1000} 秒后自动关闭`;
  }
  if (task.status === 'error' && task.flashState === 'error') {
    if (task.mode === 'row_sequence' && (task.failedStepCount ?? 0) > 0) {
      return '任务执行有错误 · 点击查看详情';
    }
    return '失败 · 点击查看详情';
  }
  if (task.mode === 'row_sequence' && task.status === 'running') {
    const stepNo = (task.sequenceStepIndex ?? 0) + 1;
    const total = task.steps?.length ?? task.total;
    return `步骤 ${stepNo}/${total}`;
  }
  return null;
}

export default function SseTaskDock({
  tasks,
  onRestore,
  onClose,
  onStop,
}: SseTaskDockProps) {
  const dockTasks = tasks.filter((t) => t.minimized);
  if (dockTasks.length === 0) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-xs">
      {dockTasks.map((task) => {
        const subtitle = dockSubtitle(task);
        const isSuccessClosing =
          task.status === 'success' &&
          task.flashState === 'success' &&
          !task.slidingOut;
        const isRunning =
          task.status === 'running' ||
          task.status === 'pending' ||
          task.status === 'queued';
        const canStop =
          isRunning && task.runId != null && typeof onStop === 'function';

        return (
          <Card
            key={task.id}
            size="small"
            hoverable={!isSuccessClosing}
            className={`group shadow-lg relative ${taskFlashClassName(task, 'sse-task-dock-card')}`}
            onClick={() => {
              if (!isSuccessClosing) {
                onRestore(task.id);
              }
            }}
            styles={{ body: { padding: '8px 12px' } }}
          >
            {!isSuccessClosing ? (
              <button
                type="button"
                aria-label="关闭任务"
                className="absolute -top-1.5 -right-1.5 z-10 flex h-5 w-5 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-500 shadow opacity-0 transition-opacity group-hover:opacity-100 hover:!opacity-100 hover:text-gray-800"
                onClick={(e) => {
                  e.stopPropagation();
                  onClose(task.id);
                }}
              >
                <CloseOutlined className="text-[10px]" />
              </button>
            ) : null}
            <div className="flex items-center gap-2">
              <DockStatusIcon task={task} />
              <div className="flex-1 min-w-0">
                <Text ellipsis className="block text-sm">
                  {task.name}
                </Text>
                {subtitle ? (
                  <Text
                    type={task.status === 'error' ? 'danger' : 'secondary'}
                    className="block text-xs"
                  >
                    {subtitle}
                  </Text>
                ) : null}
                {(task.status === 'running' ||
                  task.status === 'pending' ||
                  task.status === 'queued') && (
                  <Progress
                    percent={task.progress}
                    size="small"
                    showInfo={false}
                    className="!mb-0 !mt-1"
                  />
                )}
                {canStop ? (
                  <button
                    type="button"
                    className="mt-1 text-xs text-red-500 hover:text-red-600"
                    onClick={(e) => {
                      e.stopPropagation();
                      onStop(task.id);
                    }}
                  >
                    停止
                  </button>
                ) : null}
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
