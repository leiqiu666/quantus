import type { SseTask } from '@/store/slices/sseTaskSlice';

export function taskFlashClassName(
  task: SseTask,
  prefix: 'sse-task-modal-wrap' | 'sse-task-dock-card',
): string {
  const classes = [prefix];
  if (task.slidingOut) {
    classes.push(`${prefix}--slide-out`);
  } else if (task.flashState === 'success') {
    classes.push(`${prefix}--success-flash`);
  } else if (task.flashState === 'error') {
    classes.push(`${prefix}--error-flash`);
  }
  return classes.join(' ');
}
