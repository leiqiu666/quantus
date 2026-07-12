# Quantus Admin

Quantus 量化 Agent 管理后台 —— 基于 React 19 + Ant Design v6 + Pro Components v3 + **Vite 7** + Tailwind v4 的中后台脚手架。

## Node.js 版本

本仓库使用 **Vite 7**，要求 **Node ≥ 20.19** 或 **≥ 22.12**（Vite 内部使用 `crypto.hash`）。

推荐使用 **nvm** 与本仓库根目录的 [`.nvmrc`](./.nvmrc)：

```bash
# 安装 nvm（若尚未安装）：https://github.com/nvm-sh/nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
# 重新打开终端后：
cd quantus_admin
nvm install    # 读取 .nvmrc 安装对应版本
nvm use
node -v        # 应 ≥ 20.19 或满足 .nvmrc
```

也可使用 **fnm** / **Volta**：在项目目录执行 `fnm use` / 按工具说明读取 `.nvmrc`。

## 快速开始

```bash
# 安装依赖
pnpm install

# 启动开发服务（默认 http://localhost:5173）
pnpm dev

# 生产构建
pnpm build

# 本地预览构建产物
pnpm preview

# 代码检查
pnpm lint
pnpm typecheck
```

## 项目特性

- 「路由 / 菜单 / Tab」三位一体抽象，新增页面只改 `routes.config.tsx` 一处
- 顶部导航 + 二级（多级）侧边菜单
- 多 Tab 标签页，支持新建 / 切换 / 关闭 / 关闭其他 / 关闭全部
- 浏览器前进后退、直接输入 URL 都会自动同步到 Tab
- antd v6 CSS Variables 主题、Tailwind v4 原子样式

详细开发规范见 [CLAUDE.md](./CLAUDE.md)。

## 环境变量（根目录 `.env`）

Admin 通过 Vite 读取项目根目录 `.env`（见 `vite.config.ts` 的 `envDir`）：

| 变量 | 默认 | 说明 |
|------|------|------|
| `VITE_ETL_SSE_MAX_CONCURRENT` | `5` | SSE 补位/入库任务同时执行上限，超出排队并显示「排队中」 |

修改后需重启 `pnpm dev`。
