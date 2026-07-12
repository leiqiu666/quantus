import { useEffect, useRef } from 'react';
import { useAppDispatch } from '@/store/hooks';
import { setTaskSlidingOut, type SseTask } from '@/store/slices/sseTaskSlice';
import { SLIDE_OUT_MS, SUCCESS_AUTO_CLOSE_MS } from './taskFlashConstants';

export function useTaskFlashLifecycle(
  tasks: SseTask[],
  onClose: (id: string) => void,
) {
  const dispatch = useAppDispatch();
  const handledRef = useRef(new Set<string>());
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>[]>>(new Map());

  useEffect(() => {
    const activeIds = new Set(tasks.map((t) => t.id));

    for (const id of handledRef.current) {
      if (!activeIds.has(id)) {
        handledRef.current.delete(id);
        const timers = timersRef.current.get(id);
        timers?.forEach((timer) => window.clearTimeout(timer));
        timersRef.current.delete(id);
      }
    }

    for (const task of tasks) {
      if (handledRef.current.has(task.id)) {
        continue;
      }
      if (task.flashState === 'none') {
        continue;
      }
      if (task.status !== 'success' && task.status !== 'error') {
        continue;
      }

      handledRef.current.add(task.id);

      if (task.status === 'success' && task.flashState === 'success') {
        const slideTimer = window.setTimeout(() => {
          dispatch(setTaskSlidingOut(task.id));
        }, SUCCESS_AUTO_CLOSE_MS);
        const closeTimer = window.setTimeout(() => {
          onClose(task.id);
        }, SUCCESS_AUTO_CLOSE_MS + SLIDE_OUT_MS);
        timersRef.current.set(task.id, [slideTimer, closeTimer]);
      }
    }
  }, [tasks, dispatch, onClose]);

  useEffect(() => {
    const timers = timersRef.current;
    const handled = handledRef.current;
    return () => {
      for (const ids of timers.values()) {
        ids.forEach((timer) => window.clearTimeout(timer));
      }
      timers.clear();
      handled.clear();
    };
  }, []);
}
