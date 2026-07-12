import { configureStore } from '@reduxjs/toolkit';
import tabsReducer from './slices/tabsSlice';
import sseTaskReducer from './slices/sseTaskSlice';

/**
 * 应用全局 Redux store。
 *
 * 新增 slice 流程：
 *   1. 在 `src/store/slices/xxxSlice.ts` 创建 slice
 *   2. 在下面的 reducer 注册中加入对应字段
 *   3. 在业务组件里通过 `useAppSelector` / `useAppDispatch` 访问
 */
export const store = configureStore({
  reducer: {
    tabs: tabsReducer,
    sseTask: sseTaskReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
