#!/usr/bin/env python3
"""Tushare 文档抓取、转换、搜索工具

用法：
  python tushare_doc.py fetch <url_or_doc_id>   # 抓取单个文档并保存为 Markdown
  python tushare_doc.py search <query>           # 搜索本地文档
  python tushare_doc.py crawl [--force]          # 爬取全部文档
  python tushare_doc.py list                     # 列出所有已保存的文档
  python tushare_doc.py login                    # 扫码登录（弹出浏览器）
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

SKILL_DIR = Path(__file__).parent
DOC_DIR = SKILL_DIR / "doc"
COOKIE_FILE = SKILL_DIR / "cookies.json"
INDEX_FILE = SKILL_DIR / "doc_index.json"
TREE_FILE = SKILL_DIR / "doc_tree.json"

BASE_URL = "https://tushare.pro"


# ── HTML → Markdown ──────────────────────────────────────────────

def html_to_markdown(html: str) -> str:
    """将 tushare 文档 HTML 转为 Markdown"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    # 移除搜索面板
    for sp in soup.find_all(class_="search-panel"):
        sp.decompose()

    lines = []

    for el in soup.children:
        if not hasattr(el, "name") or el.name is None:
            text = str(el).strip()
            if text:
                lines.append(text)
            continue

        if el.name == "h2":
            text = el.get_text(strip=True)
            if text:
                lines.append(f"\n## {text}\n")

        elif el.name == "hr":
            lines.append("\n---\n")

        elif el.name == "p":
            # Check if it's a section header like <strong>输入参数</strong>
            strong = el.find("strong")
            if strong and strong.get_text(strip=True) in (
                "输入参数", "输出参数", "接口使用", "接口示例",
                "数据示例", "数据样例", "使用示例", "调用示例",
                "数据说明", "注意事项",
            ):
                lines.append(f"\n### {strong.get_text(strip=True)}\n")
                # Process remaining text in the paragraph
                remaining = el.get_text().replace(strong.get_text(), "").strip()
                if remaining:
                    lines.append(remaining)
            else:
                text = _process_inline(el)
                if text.strip():
                    lines.append(text.strip())

        elif el.name == "table":
            lines.append(_table_to_md(el))

        elif el.name == "div" and "codehilite" in el.get("class", []):
            code_el = el.find("code")
            if code_el:
                code_text = code_el.get_text()
            else:
                code_text = el.get_text()
            lines.append(f"\n```python\n{code_text.strip()}\n```\n")

        elif el.name == "div":
            text = el.get_text(strip=True)
            if text:
                lines.append(text)

    # Clean up multiple blank lines
    result = "\n".join(lines)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def _process_inline(el) -> str:
    """处理行内元素（p, span, a, br 等）"""
    parts = []
    for child in el.children:
        if not hasattr(child, "name") or child.name is None:
            parts.append(str(child))
        elif child.name == "br":
            parts.append("  \n")
        elif child.name == "a":
            href = child.get("href", "")
            text = child.get_text(strip=True)
            if href and not href.startswith("javascript"):
                if href.startswith("/"):
                    href = BASE_URL + href
                parts.append(f"[{text}]({href})")
            else:
                parts.append(text)
        elif child.name == "strong":
            parts.append(f"**{child.get_text(strip=True)}**")
        elif child.name == "code":
            parts.append(f"`{child.get_text(strip=True)}`")
        elif child.name == "em":
            parts.append(f"*{child.get_text(strip=True)}*")
        else:
            parts.append(child.get_text())
    return "".join(parts)


def _table_to_md(table_el) -> str:
    """将 HTML table 转为 Markdown 表格"""
    rows = []

    thead = table_el.find("thead")
    if thead:
        for tr in thead.find_all("tr"):
            cells = [th.get_text(strip=True) for th in tr.find_all(["th", "td"])]
            rows.append(cells)

    tbody = table_el.find("tbody")
    body_rows = tbody.find_all("tr") if tbody else table_el.find_all("tr")
    if not tbody:
        body_rows = body_rows[1:]  # skip header if no thead

    for tr in body_rows:
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        rows.append(cells)

    if not rows:
        return ""

    # Normalize column count
    max_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < max_cols:
            r.append("")

    # Build markdown table
    lines = []
    # Header
    lines.append("| " + " | ".join(rows[0]) + " |")
    lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    # Body
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n" + "\n".join(lines) + "\n"


# ── Cookie 管理 ──────────────────────────────────────────────────

def load_cookies() -> list:
    if not COOKIE_FILE.exists():
        print(f"[!] Cookie 文件不存在: {COOKIE_FILE}", file=sys.stderr)
        print("    请先运行 `python tushare_doc.py login` 扫码登录", file=sys.stderr)
        sys.exit(1)
    return json.loads(COOKIE_FILE.read_text())


def save_cookies(cookies: list):
    COOKIE_FILE.write_text(json.dumps(cookies, indent=2, ensure_ascii=False))


# ── Playwright 抓取 ──────────────────────────────────────────────

def login():
    """弹出浏览器让用户扫码登录，保存 cookie"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("[1] 打开 tushare 登录页...", flush=True)
        page.goto(f"{BASE_URL}/document/2?doc_id=162",
                   wait_until="domcontentloaded", timeout=60000)
        print("[2] 请在浏览器中微信扫码登录（等待5分钟）", flush=True)

        initial_count = len(context.cookies())
        start = time.time()
        logged_in = False

        while time.time() - start < 300:
            cookies = context.cookies()
            if len(cookies) > initial_count + 1:
                logged_in = True
                print(f"[3] 登录成功！", flush=True)
                break
            elapsed = int(time.time() - start)
            if elapsed % 15 == 0 and elapsed > 0:
                print(f"    ... {elapsed}s", flush=True)
            time.sleep(3)

        if not logged_in:
            print("[!] 超时", flush=True)
            browser.close()
            sys.exit(1)

        save_cookies(context.cookies())
        print(f"[4] Cookie 已保存到 {COOKIE_FILE}", flush=True)
        browser.close()


def fetch_page(doc_id: int, cookies: list, headless: bool = True) -> str:
    """用 Playwright 抓取单个文档页面的 HTML"""
    from playwright.sync_api import sync_playwright

    url = f"{BASE_URL}/document/2?doc_id={doc_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=headless)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()

        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)

        content_el = page.query_selector(".content")
        if not content_el:
            browser.close()
            raise RuntimeError(f"未找到 .content 元素 (doc_id={doc_id})")

        html = content_el.inner_html()
        text = content_el.inner_text()

        if "微信扫码登录" in text:
            browser.close()
            raise RuntimeError(
                f"Cookie 已过期，请重新登录: python tushare_doc.py login"
            )

        browser.close()
        return html


def expand_sidebar(cookies: list) -> list:
    """展开侧边栏获取全部文档链接"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()

        page.goto(f"{BASE_URL}/document/2?doc_id=162",
                   wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # Expand all closed tree nodes
        for _ in range(20):
            closed = page.query_selector_all(".jstree-closed")
            if not closed:
                break
            for node in closed:
                toggle = node.query_selector(".jstree-ocl")
                if toggle:
                    toggle.click()
                    time.sleep(0.2)
            time.sleep(0.5)

        links = page.evaluate("""() => {
            const sidebar = document.querySelector('.sidebar');
            if (!sidebar) return [];
            const links = sidebar.querySelectorAll('a[href*="doc_id"]');
            return Array.from(links).map(a => {
                const li = a.closest('li');
                const level = parseInt(li?.getAttribute('aria-level') || '0');
                const isLeaf = li?.classList.contains('jstree-leaf') || false;
                const href = a.getAttribute('href') || '';
                const match = href.match(/doc_id=(\\d+)/);
                const docId = match ? parseInt(match[1]) : null;
                return {
                    doc_id: docId,
                    text: a.innerText?.trim() || '',
                    level,
                    isLeaf,
                };
            });
        }""")

        browser.close()
        return links


# ── Index 管理 ───────────────────────────────────────────────────

def load_index() -> dict:
    if INDEX_FILE.exists():
        return json.loads(INDEX_FILE.read_text())
    return {}


def save_index(index: dict):
    INDEX_FILE.write_text(json.dumps(index, indent=2, ensure_ascii=False))


def update_index(doc_id: int, metadata: dict):
    index = load_index()
    index[str(doc_id)] = {
        **metadata,
        "doc_id": doc_id,
        "url": f"{BASE_URL}/document/2?doc_id={doc_id}",
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    save_index(index)


# ── 命令实现 ─────────────────────────────────────────────────────

def parse_doc_id(url_or_id: str) -> int:
    """从 URL 或纯数字中解析 doc_id"""
    if url_or_id.isdigit():
        return int(url_or_id)
    parsed = urlparse(url_or_id)
    qs = parse_qs(parsed.query)
    if "doc_id" in qs:
        return int(qs["doc_id"][0])
    # Try to find doc_id in path
    m = re.search(r"doc_id=(\d+)", url_or_id)
    if m:
        return int(m.group(1))
    raise ValueError(f"无法解析 doc_id: {url_or_id}")


def cmd_fetch(args):
    """抓取单个文档"""
    doc_id = parse_doc_id(args.url_or_id)
    cookies = load_cookies()

    print(f"[1] 抓取 doc_id={doc_id}...", flush=True)
    html = fetch_page(doc_id, cookies, headless=not args.visible)

    print(f"[2] 转换 HTML → Markdown...", flush=True)
    md = html_to_markdown(html)

    # Extract metadata
    title_match = re.search(r"^## (.+)$", md, re.MULTILINE)
    title = title_match.group(1) if title_match else f"doc_{doc_id}"

    # Extract API name (接口：xxx)
    api_match = re.search(r"接口[：:]\s*([a-zA-Z_][a-zA-Z0-9_]*)", md)
    api_name = api_match.group(1) if api_match else ""

    # Save markdown
    safe_name = re.sub(r'[^\w一-鿿-]', '_', api_name or title)
    filename = f"{doc_id}_{safe_name}.md"
    filepath = DOC_DIR / filename
    DOC_DIR.mkdir(exist_ok=True)

    # Add frontmatter
    full_md = f"""---
doc_id: {doc_id}
title: "{title}"
api_name: "{api_name}"
url: "{BASE_URL}/document/2?doc_id={doc_id}"
---

{md}
"""
    filepath.write_text(full_md, encoding="utf-8")

    # Update index
    update_index(doc_id, {
        "title": title,
        "api_name": api_name,
        "filename": filename,
    })

    print(f"[3] 已保存: {filepath}", flush=True)
    print(f"    标题: {title}", flush=True)
    print(f"    接口: {api_name}", flush=True)
    print(f"    在线: {BASE_URL}/document/2?doc_id={doc_id}", flush=True)

    if args.output:
        print(f"\n{md}")

    return filepath


def cmd_search(args):
    """搜索本地文档"""
    query = args.query.lower()
    index = load_index()

    if not index:
        print("[!] 本地文档为空，请先运行 crawl 抓取文档", file=sys.stderr)
        sys.exit(1)

    results = []
    keywords = query.split()

    for doc_id, meta in index.items():
        score = 0
        title = meta.get("title", "").lower()
        api_name = meta.get("api_name", "").lower()
        filename = meta.get("filename", "")

        # Score by metadata match
        for kw in keywords:
            if kw in api_name:
                score += 10
            if kw in title:
                score += 5

        # Score by content match
        filepath = DOC_DIR / filename
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8").lower()
            for kw in keywords:
                count = content.count(kw)
                if count > 0:
                    score += min(count, 5)  # cap per-keyword content score

        if score > 0:
            results.append((score, doc_id, meta))

    results.sort(key=lambda x: -x[0])

    if not results:
        print(f"未找到匹配 '{args.query}' 的文档")
        return

    print(f"找到 {len(results)} 个匹配结果:\n")
    for i, (score, doc_id, meta) in enumerate(results[:20], 1):
        title = meta.get("title", "?")
        api_name = meta.get("api_name", "")
        url = meta.get("url", "")
        print(f"  {i:2d}. [{score:3d}分] {api_name or title}")
        print(f"      doc_id={doc_id}  {url}")
        if api_name:
            print(f"      标题: {title}")
        print()

    # Show full content of top result
    if results and args.detail:
        _, _, top_meta = results[0]
        filepath = DOC_DIR / top_meta["filename"]
        if filepath.exists():
            print(f"{'='*60}")
            print(f"最佳匹配完整内容: {top_meta.get('api_name', top_meta.get('title'))}")
            print(f"{'='*60}")
            print(filepath.read_text(encoding="utf-8"))


def _node_doc_id(node: dict) -> int | None:
    """从树节点中提取 doc_id（优先用 doc_id 字段，回退解析 href）"""
    if node.get("doc_id"):
        return node["doc_id"]
    href = node.get("href", "")
    m = re.search(r"doc_id=(\d+)", href)
    return int(m.group(1)) if m else None


def cmd_crawl(args):
    """爬取全部文档"""
    cookies = load_cookies()
    DOC_DIR.mkdir(exist_ok=True)
    index = load_index()

    # Get doc tree (from sidebar)
    if TREE_FILE.exists() and not args.refresh_tree:
        tree = json.loads(TREE_FILE.read_text())
    else:
        print("[1] 展开侧边栏获取文档列表...", flush=True)
        tree = expand_sidebar(cookies)
        TREE_FILE.write_text(json.dumps(tree, indent=2, ensure_ascii=False))
        print(f"    文档树已保存到 {TREE_FILE}", flush=True)

    # Filter leaf nodes (actual API docs)
    leaves = [n for n in tree if n.get("isLeaf")]
    if not leaves:
        # If no leaf nodes, use all nodes with doc_id
        leaves = [n for n in tree if _node_doc_id(n)]

    # Parse doc_id for each leaf
    for node in leaves:
        node["_doc_id"] = _node_doc_id(node)
    leaves = [n for n in leaves if n["_doc_id"]]

    total = len(leaves)
    print(f"[2] 共 {total} 个文档待抓取", flush=True)

    # Check which ones we already have
    skipped = 0
    to_fetch = []
    for node in leaves:
        doc_id = node["_doc_id"]
        if not args.force and str(doc_id) in index:
            skipped += 1
        else:
            to_fetch.append(node)

    if skipped:
        print(f"    跳过已存在的 {skipped} 个（用 --force 强制更新）", flush=True)
    print(f"    待抓取: {len(to_fetch)} 个", flush=True)

    if not to_fetch:
        print("[3] 全部文档已是最新", flush=True)
        return

    # Fetch one by one with Playwright (reuse browser session)
    from playwright.sync_api import sync_playwright

    success = 0
    failed = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()

        for i, node in enumerate(to_fetch, 1):
            doc_id = node["_doc_id"]
            label = node.get("text", f"doc_{doc_id}")
            url = f"{BASE_URL}/document/2?doc_id={doc_id}"

            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(2000)

                content_el = page.query_selector(".content")
                if not content_el:
                    print(f"  [{i}/{len(to_fetch)}] FAIL {label} (doc_id={doc_id}): 无 .content", flush=True)
                    failed += 1
                    continue

                html = content_el.inner_html()
                text = content_el.inner_text()

                if "微信扫码登录" in text:
                    print(f"  [!] Cookie 已过期，请重新登录: python tushare_doc.py login", flush=True)
                    break

                md = html_to_markdown(html)

                # Extract metadata
                title_match = re.search(r"^## (.+)$", md, re.MULTILINE)
                title = title_match.group(1) if title_match else label

                api_match = re.search(r"接口[：:]\s*([a-zA-Z_][a-zA-Z0-9_]*)", md)
                api_name = api_match.group(1) if api_match else ""

                safe_name = re.sub(r'[^\w一-鿿-]', '_', api_name or title)
                filename = f"{doc_id}_{safe_name}.md"
                filepath = DOC_DIR / filename

                full_md = f"""---
doc_id: {doc_id}
title: "{title}"
api_name: "{api_name}"
url: "{url}"
---

{md}
"""
                filepath.write_text(full_md, encoding="utf-8")
                update_index(doc_id, {
                    "title": title,
                    "api_name": api_name,
                    "filename": filename,
                })

                success += 1
                print(f"  [{i}/{len(to_fetch)}] OK   {api_name or title} (doc_id={doc_id})", flush=True)

            except Exception as e:
                failed += 1
                print(f"  [{i}/{len(to_fetch)}] FAIL {label} (doc_id={doc_id}): {e}", flush=True)

            # Rate limit: 1-2s between pages
            time.sleep(1.5)

        browser.close()

    print(f"\n[完成] 成功: {success}, 失败: {failed}, 跳过: {skipped}, 总计: {total}", flush=True)


def cmd_list(args):
    """列出所有已保存的文档"""
    index = load_index()
    if not index:
        print("本地无文档")
        return

    print(f"共 {len(index)} 个文档:\n")
    for doc_id in sorted(index.keys(), key=lambda x: int(x)):
        meta = index[doc_id]
        api = meta.get("api_name", "")
        title = meta.get("title", "")
        url = meta.get("url", "")
        print(f"  {doc_id:>4s}  {api:30s}  {title}  {url}")


# ── CLI 入口 ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Tushare 文档工具")
    sub = parser.add_subparsers(dest="command")

    # login
    sub.add_parser("login", help="扫码登录")

    # fetch
    p_fetch = sub.add_parser("fetch", help="抓取单个文档")
    p_fetch.add_argument("url_or_id", help="文档 URL 或 doc_id")
    p_fetch.add_argument("--output", "-o", action="store_true", help="输出 Markdown 到 stdout")
    p_fetch.add_argument("--visible", "-v", action="store_true", help="显示浏览器窗口")

    # search
    p_search = sub.add_parser("search", help="搜索本地文档")
    p_search.add_argument("query", help="搜索关键词（支持多个，空格分隔）")
    p_search.add_argument("--detail", "-d", action="store_true", help="显示最佳匹配的完整内容")

    # crawl
    p_crawl = sub.add_parser("crawl", help="爬取全部文档")
    p_crawl.add_argument("--force", "-f", action="store_true", help="强制更新已存在的文档")
    p_crawl.add_argument("--refresh-tree", action="store_true", help="重新抓取文档树")

    # list
    sub.add_parser("list", help="列出已保存的文档")

    args = parser.parse_args()

    if args.command == "login":
        login()
    elif args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "crawl":
        cmd_crawl(args)
    elif args.command == "list":
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
