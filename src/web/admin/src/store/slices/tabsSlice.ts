import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

/**
 * Tab 标签页项。key 直接使用路由的完整 path，保证全局唯一。
 */
export interface TabItem {
  /** 路由完整 path，如 `/demo/page1` */
  key: string;
  /** Tab 显示标题（来自 RouteConfig.name） */
  label: string;
  /** 是否允许关闭（首页等可设为 false） */
  closable: boolean;
}

export interface TabsState {
  tabs: TabItem[];
  activeKey: string;
}

const initialState: TabsState = {
  tabs: [],
  activeKey: '',
};

const tabsSlice = createSlice({
  name: 'tabs',
  initialState,
  reducers: {
    /** 打开（或激活）一个 Tab —— 已存在则只更新 activeKey */
    addTab(state, action: PayloadAction<TabItem>) {
      const tab = action.payload;
      const existed = state.tabs.find((t) => t.key === tab.key);
      if (!existed) {
        state.tabs.push(tab);
      }
      state.activeKey = tab.key;
    },

    /** 关闭指定 Tab。返回应该被激活的下一个 key（在外部 hook 中处理 navigate） */
    removeTab(state, action: PayloadAction<string>) {
      const key = action.payload;
      const idx = state.tabs.findIndex((t) => t.key === key);
      if (idx === -1) return;
      const target = state.tabs[idx];
      if (!target.closable) return; // 不可关闭则忽略

      state.tabs.splice(idx, 1);

      if (state.activeKey === key) {
        const next = state.tabs[idx] ?? state.tabs[idx - 1];
        state.activeKey = next ? next.key : '';
      }
    },

    /** 切换激活 Tab */
    setActive(state, action: PayloadAction<string>) {
      state.activeKey = action.payload;
    },

    /** 关闭其他：保留指定 key 与所有不可关闭项 */
    closeOthers(state, action: PayloadAction<string>) {
      const key = action.payload;
      state.tabs = state.tabs.filter((t) => t.key === key || !t.closable);
      state.activeKey = key;
    },

    /** 关闭全部：仅保留不可关闭项 */
    closeAll(state) {
      state.tabs = state.tabs.filter((t) => !t.closable);
      state.activeKey = state.tabs[0]?.key ?? '';
    },
  },
});

export const { addTab, removeTab, setActive, closeOthers, closeAll } =
  tabsSlice.actions;

export default tabsSlice.reducer;
