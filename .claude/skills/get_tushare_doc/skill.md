---
name: get_tushare_doc
description: |
  获取 Tushare 接口文档并转为 Markdown。支持三种用法：
  1. 给文档 URL 或 doc_id，抓取最新文档并保存到本地
  2. 给接口名称、字段名、数据内容等关键词，搜索本地已保存的文档
  3. 全盘扫描所有 Tushare 文档保存到本地

  用法示例：
  - "帮我看看 https://tushare.pro/document/2?doc_id=162 这个接口"
  - "查一下 tushare 的 daily 接口文档"
  - "tushare 哪个接口有 ts_code 和 trade_date 字段"
  - "抓取全部 tushare 文档"
  - "/get_tushare_doc fetch 162"
  - "/get_tushare_doc search daily trade_date"
  - "/get_tushare_doc crawl"
---

# Tushare 文档抓取与搜索

## 工具路径

脚本位于：`.claude/skills/get_tushare_doc/tushare_doc.py`
文档保存目录：`.claude/skills/get_tushare_doc/doc/`
文档索引：`.claude/skills/get_tushare_doc/doc_index.json`

## 前置条件

需要已登录的 Cookie。如果 Cookie 过期或缺失，运行：
```bash
uv run python .claude/skills/get_tushare_doc/tushare_doc.py login
```
会弹出浏览器窗口，用微信扫码登录后自动保存 Cookie。

## 三种能力

### 能力 1：按 URL/doc_id 抓取文档

用户提供 tushare 文档链接（如 `https://tushare.pro/document/2?doc_id=162`）或 doc_id 时：

```bash
uv run python .claude/skills/get_tushare_doc/tushare_doc.py fetch <url_or_doc_id> -o
```

- `-o` 参数会同时输出 Markdown 到 stdout
- 文档自动保存到 `doc/` 目录，覆盖已有文件
- 更新 `doc_index.json` 索引

执行后，将输出的 Markdown 内容展示给用户，并告知在线地址。

### 能力 2：搜索本地文档

用户提供接口名称、字段名、数据内容等关键词时：

```bash
uv run python .claude/skills/get_tushare_doc/tushare_doc.py search "<关键词>" -d
```

- 支持多个关键词（空格分隔），取交集
- 搜索范围：接口名、标题、全文内容
- `-d` 参数显示最佳匹配的完整 Markdown
- 结果包含在线地址

如果本地没有文档（索引为空），提示用户先运行 crawl 或 fetch。

### 能力 3：全盘爬取

用户要求抓取全部文档时：

```bash
uv run python .claude/skills/get_tushare_doc/tushare_doc.py crawl
```

- 自动展开侧边栏获取全部 ~237 个文档
- 跳过已存在的文档（用 `--force` 强制更新全部）
- `--refresh-tree` 重新抓取文档树结构
- 每个文档间隔 1.5 秒，全量约 6 分钟

## 输出格式

抓取到的 Markdown 包含以下结构：
- `## 标题` — 文档标题
- 接口描述段落（接口名、描述、限量、积分要求）
- `### 输入参数` — Markdown 表格
- `### 输出参数` — Markdown 表格
- `### 接口使用` / `### 接口示例` — Python 代码块
- `### 数据示例` / `### 数据样例` — 数据样例代码块

## 回复规范

1. 抓取成功后：展示完整 Markdown 内容 + 在线地址链接
2. 搜索成功后：列出匹配结果（接口名、doc_id、在线地址），如用户需要则展示完整内容
3. 如果 Cookie 过期报错，提示用户运行 login 命令重新扫码
