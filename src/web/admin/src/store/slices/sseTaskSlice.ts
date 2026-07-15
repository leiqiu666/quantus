import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

export type SseTaskStatus = 'queued' | 'pending' | 'running' | 'success' | 'error';

export type SseTaskMode =
  | 'report_history'
  | 'etl_generic'
  | 'schedule_job'
  | 'row_sequence';

export interface SseTaskStep {
  taskKey: string;
  label: string;
  startDate: string;
  endDate?: string;
  mode: Exclude<SseTaskMode, 'row_sequence' | 'schedule_job'>;
  columnKey?: string;
  threshold?: number;
}

export type SseTaskFlashState = 'none' | 'success' | 'error';

/** 回测 SSE 附加参数（task_key=backtest_run） */
export interface BacktestSseParams {
  backtestMode: 'single' | 'combo';
  factorName?: string;
  comboId?: number;
  groups?: number;
  rebalance?: string;
  commissionRate?: number;
  stampDutyRate?: number;
  slippageRate?: number;
}

/** 单因子计算 SSE（task_key=factor_compute） */
export interface FactorComputeSseParams {
  factorName: string;
  force?: boolean;
}

export interface SseTask {
  id: string;
  name: string;
  mode: SseTaskMode;
  taskKey: string;
  jobKey?: string;
  startDate: string;
  endDate?: string;
  status: SseTaskStatus;
  progress: number;
  total: number;
  currentIndex: number;
  logs: string[];
  minimized: boolean;
  expanded: boolean;
  steps?: SseTaskStep[];
  sequenceStepIndex?: number;
  currentStepLabel?: string;
  dashboardGroupId?: string;
  dashboardDateKey?: string;
  failedStepCount?: number;
  sequenceStepErrors?: { label: string; message: string }[];
  flashState: SseTaskFlashState;
  slidingOut: boolean;
  backtest?: BacktestSseParams;
  factorCompute?: FactorComputeSseParams;
  runId?: number;
}

interface SseTaskState {
  tasks: SseTask[];
}

const initialState: SseTaskState = {
  tasks: [],
};

function formatLog(message: string): string {
  const ts = new Date().toLocaleTimeString('zh-CN', { hour12: false });
  return `[${ts}] ${message}`;
}

function stripLogTs(log: string): string {
  return log.replace(/^\[[^\]]+\]\s*/, '');
}

function findLastLogIndex(logs: string[], pred: (bare: string) => boolean): number {
  for (let i = logs.length - 1; i >= 0; i -= 1) {
    if (pred(stripLogTs(logs[i]))) {
      return i;
    }
  }
  return -1;
}

function baseTaskFields(
  payload: {
    id: string;
    name: string;
    mode: SseTaskMode;
    taskKey: string;
    jobKey?: string;
    startDate: string;
    endDate?: string;
    backtest?: BacktestSseParams;
    factorCompute?: FactorComputeSseParams;
  },
  ui: { expanded: boolean; minimized: boolean },
): SseTask {
  return {
    id: payload.id,
    name: payload.name,
    mode: payload.mode,
    taskKey: payload.taskKey,
    jobKey: payload.jobKey,
    startDate: payload.startDate,
    endDate: payload.endDate,
    backtest: payload.backtest,
    factorCompute: payload.factorCompute,
    status: 'queued',
    progress: 0,
    total: 0,
    currentIndex: 0,
    logs: [],
    flashState: 'none',
    slidingOut: false,
    ...ui,
  };
}

const sseTaskSlice = createSlice({
  name: 'sseTask',
  initialState,
  reducers: {
    addTask(
      state,
      action: PayloadAction<{
        id: string;
        name: string;
        mode: Exclude<SseTaskMode, 'row_sequence'>;
        taskKey: string;
        jobKey?: string;
        startDate: string;
        endDate?: string;
        backtest?: BacktestSseParams;
        factorCompute?: FactorComputeSseParams;
      }>,
    ) {
      state.tasks.forEach((t) => {
        t.expanded = false;
      });
      state.tasks.push(
        baseTaskFields(action.payload, { expanded: true, minimized: false }),
      );
    },
    addRowSequenceTask(
      state,
      action: PayloadAction<{
        id: string;
        name: string;
        startDate: string;
        endDate?: string;
        dashboardGroupId?: string;
        dashboardDateKey?: string;
        steps: SseTaskStep[];
      }>,
    ) {
      state.tasks.forEach((t) => {
        t.expanded = false;
      });
      const steps = action.payload.steps;
      state.tasks.push({
        ...baseTaskFields(
          {
            id: action.payload.id,
            name: action.payload.name,
            mode: 'row_sequence',
            taskKey: 'row_sequence',
            startDate: action.payload.startDate,
            endDate: action.payload.endDate,
          },
          { expanded: true, minimized: false },
        ),
        steps,
        dashboardGroupId: action.payload.dashboardGroupId,
        dashboardDateKey: action.payload.dashboardDateKey,
        failedStepCount: 0,
        sequenceStepErrors: [],
        sequenceStepIndex: 0,
        currentStepLabel: steps[0]?.label,
        total: steps.length,
        currentIndex: 0,
        progress: 0,
      });
    },
    setTaskRunning(state, action: PayloadAction<string>) {
      const task = state.tasks.find((t) => t.id === action.payload);
      if (task) {
        task.status = 'running';
      }
    },
    promoteTaskFromQueue(state, action: PayloadAction<string>) {
      const task = state.tasks.find((t) => t.id === action.payload);
      if (task && task.status === 'queued') {
        task.status = 'pending';
      }
    },
    setSequenceStep(
      state,
      action: PayloadAction<{
        id: string;
        stepIndex: number;
        stepLabel: string;
      }>,
    ) {
      const { id, stepIndex, stepLabel } = action.payload;
      const task = state.tasks.find((t) => t.id === id);
      if (!task || !task.steps?.length) {
        return;
      }
      task.status = 'running';
      task.sequenceStepIndex = stepIndex;
      task.currentStepLabel = stepLabel;
      task.total = task.steps.length;
      task.currentIndex = stepIndex;
      task.progress =
        task.total > 0 ? Math.round((stepIndex / task.total) * 100) : 0;
      task.logs.push(
        formatLog(`—— 步骤 ${stepIndex + 1}/${task.total}：${stepLabel} ——`),
      );
    },
    completeSequenceStep(
      state,
      action: PayloadAction<{
        id: string;
        stepIndex: number;
        message: string;
      }>,
    ) {
      const { id, stepIndex, message } = action.payload;
      const task = state.tasks.find((t) => t.id === id);
      if (!task || !task.steps?.length) {
        return;
      }
      task.currentIndex = stepIndex + 1;
      task.progress =
        task.total > 0
          ? Math.round(((stepIndex + 1) / task.total) * 100)
          : 100;
      task.logs.push(formatLog(message));
    },
    setTaskTotal(
      state,
      action: PayloadAction<{ id: string; total: number }>,
    ) {
      const task = state.tasks.find((t) => t.id === action.payload.id);
      if (task) {
        task.total = action.payload.total;
        task.progress = 0;
      }
    },
    setTaskRunId(
      state,
      action: PayloadAction<{ id: string; runId: number }>,
    ) {
      const task = state.tasks.find((t) => t.id === action.payload.id);
      if (task) {
        task.runId = action.payload.runId;
      }
    },
    updateTaskProgress(
      state,
      action: PayloadAction<{
        id: string;
        index: number;
        total: number;
        period: string;
        saved: number;
        logMessage?: string;
      }>,
    ) {
      const { id, index, total, period, saved, logMessage } = action.payload;
      const task = state.tasks.find((t) => t.id === id);
      if (!task) {
        return;
      }
      task.status = 'running';
      task.currentIndex = index;
      task.total = total;
      task.progress = total > 0 ? Math.round((index / total) * 100) : 0;
      const message =
        logMessage ?? `第 ${index}/${total} 期 ${period} 入库 ${saved} 条`;
      // 调度：用完成日志替换同一步的百分比行，并刷新时间戳
      if (task.mode === 'schedule_job') {
        const prefix = `第 ${index}/${total} 步 ${period}`;
        const found = findLastLogIndex(task.logs, (bare) => bare.startsWith(prefix));
        const line = formatLog(message);
        if (found >= 0) {
          task.logs[found] = line;
        } else {
          task.logs.push(line);
        }
        return;
      }
      task.logs.push(formatLog(message));
    },
    /** 调度命令内部进度：就地更新「第 N/M 步 label XX%」，100% 时刷新时间 */
    updateScheduleCommandProgress(
      state,
      action: PayloadAction<{
        id: string;
        cmdIndex: number;
        cmdTotal: number;
        cmdLabel: string;
        cmdPct: number;
      }>,
    ) {
      const { id, cmdIndex, cmdTotal, cmdLabel, cmdPct } = action.payload;
      const task = state.tasks.find((t) => t.id === id);
      if (!task) {
        return;
      }
      task.status = 'running';
      task.currentIndex = Math.max(0, cmdIndex - 1);
      task.total = cmdTotal;
      const pct = Math.min(100, Math.max(0, cmdPct));
      // 总进度条 = 已完成命令 + 当前命令内百分比
      const frac = (Math.max(0, cmdIndex - 1) + pct / 100) / Math.max(cmdTotal, 1);
      task.progress = Math.round(frac * 100);
      task.currentStepLabel = cmdLabel;

      if (task.mode === 'row_sequence') {
        task.sequenceStepIndex = Math.max(0, cmdIndex - 1);
      }

      const prefix = `第 ${cmdIndex}/${cmdTotal} 步 ${cmdLabel}`;
      const message = `${prefix} ${pct}%`;
      const found = findLastLogIndex(task.logs, (bare) => bare.startsWith(prefix));
      if (found >= 0) {
        if (pct >= 100) {
          task.logs[found] = formatLog(message);
        } else {
          const oldTs = task.logs[found].match(/^\[([^\]]+)\]/)?.[1];
          task.logs[found] = oldTs ? `[${oldTs}] ${message}` : formatLog(message);
        }
      } else {
        task.logs.push(formatLog(message));
      }
    },
    appendTaskLog(
      state,
      action: PayloadAction<{ id: string; message: string }>,
    ) {
      const task = state.tasks.find((t) => t.id === action.payload.id);
      if (task) {
        task.logs.push(formatLog(action.payload.message));
      }
    },
    failSequenceStep(
      state,
      action: PayloadAction<{
        id: string;
        stepIndex: number;
        label: string;
        message: string;
      }>,
    ) {
      const { id, stepIndex, label, message } = action.payload;
      const task = state.tasks.find((t) => t.id === id);
      if (!task || !task.steps?.length) {
        return;
      }
      task.currentIndex = stepIndex + 1;
      task.progress =
        task.total > 0
          ? Math.round(((stepIndex + 1) / task.total) * 100)
          : 100;
      task.failedStepCount = (task.failedStepCount ?? 0) + 1;
      if (!task.sequenceStepErrors) {
        task.sequenceStepErrors = [];
      }
      task.sequenceStepErrors.push({ label, message });
      task.logs.push(formatLog(`错误 · ${label}：${message}`));
    },
    finishRowSequenceTask(
      state,
      action: PayloadAction<{
        id: string;
        failedCount: number;
        totalSteps: number;
      }>,
    ) {
      const { id, failedCount, totalSteps } = action.payload;
      const task = state.tasks.find((t) => t.id === id);
      if (!task) {
        return;
      }
      task.progress = 100;
      task.currentIndex = totalSteps;
      if (failedCount > 0) {
        task.status = 'error';
        task.logs.push(
          formatLog(
            `任务执行有错误（${failedCount}/${totalSteps} 列失败，其余列已继续执行）`,
          ),
        );
      } else {
        task.status = 'success';
        task.logs.push(formatLog('行级补位全部完成'));
      }
    },
    setTaskSuccess(
      state,
      action: PayloadAction<{ id: string; message?: string }>,
    ) {
      const task = state.tasks.find((t) => t.id === action.payload.id);
      if (!task) {
        return;
      }
      task.status = 'success';
      task.progress = 100;
      if (action.payload.message) {
        task.logs.push(formatLog(action.payload.message));
      }
    },
    setTaskError(
      state,
      action: PayloadAction<{ id: string; message: string }>,
    ) {
      const task = state.tasks.find((t) => t.id === action.payload.id);
      if (!task) {
        return;
      }
      task.status = 'error';
      task.logs.push(formatLog(`错误: ${action.payload.message}`));
    },
    setTaskFlash(
      state,
      action: PayloadAction<{ id: string; flash: SseTaskFlashState }>,
    ) {
      const task = state.tasks.find((t) => t.id === action.payload.id);
      if (task) {
        task.flashState = action.payload.flash;
      }
    },
    setTaskSlidingOut(state, action: PayloadAction<string>) {
      const task = state.tasks.find((t) => t.id === action.payload);
      if (task) {
        task.slidingOut = true;
      }
    },
    minimizeTask(state, action: PayloadAction<string>) {
      const task = state.tasks.find((t) => t.id === action.payload);
      if (task) {
        task.minimized = true;
        task.expanded = false;
      }
    },
    restoreTask(state, action: PayloadAction<string>) {
      state.tasks.forEach((t) => {
        t.expanded = t.id === action.payload;
        if (t.id === action.payload) {
          t.minimized = false;
        }
      });
    },
    closeTask(state, action: PayloadAction<string>) {
      state.tasks = state.tasks.filter((t) => t.id !== action.payload);
    },
  },
});

export const {
  addTask,
  addRowSequenceTask,
  promoteTaskFromQueue,
  setTaskRunning,
  setSequenceStep,
  completeSequenceStep,
  failSequenceStep,
  finishRowSequenceTask,
  setTaskTotal,
  setTaskRunId,
  updateTaskProgress,
  updateScheduleCommandProgress,
  appendTaskLog,
  setTaskSuccess,
  setTaskError,
  setTaskFlash,
  setTaskSlidingOut,
  minimizeTask,
  restoreTask,
  closeTask,
} = sseTaskSlice.actions;

export default sseTaskSlice.reducer;
