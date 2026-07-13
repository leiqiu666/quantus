#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本机 Git 远端开关：推完代码后可立刻清掉本机 origin 痕迹；需要再 push 时再加回来。

【清理】去掉 origin、upstream、refs/remotes、FETCH_HEAD（本地 commit 保留，不动 GitHub）
  python scripts/git_origin.py clean
  # 或
  uv run python scripts/git_origin.py clean

【增加 origin】
  python scripts/git_origin.py add git@github.com:xxx/xxx.git
  # 若已存在 origin，会先删再加（等价换 URL）

【可选】指定仓库根目录（默认：本脚本所在仓库根，即 quantus/）
  python scripts/git_origin.py --repo /path/to/quantus clean
  python scripts/git_origin.py --repo /path/to/quantus add git@github.com:leiqiu666/quantus.git

典型流程：
  1) python scripts/git_origin.py add git@github.com:leiqiu666/quantus.git
  2) git push -u origin main
  3) python scripts/git_origin.py clean
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _run(repo: Path, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        text=True,
        capture_output=True,
    )


def _git_root_default() -> Path:
    here = Path(__file__).resolve().parent
    # scripts/ -> 仓库根
    if (here.parent / ".git").exists():
        return here.parent
    cwd = Path.cwd()
    if (cwd / ".git").exists():
        return cwd
    raise SystemExit("找不到 .git：请在仓库内运行，或用 --repo 指定根目录")


def cmd_clean(repo: Path) -> None:
    if not (repo / ".git").is_dir():
        raise SystemExit(f"不是 git 仓库: {repo}")

    # remote
    remotes = _run(repo, ["remote"], check=False).stdout.split()
    for name in remotes:
        _run(repo, ["remote", "remove", name], check=False)
        print(f"removed remote: {name}")

    # branch upstream（常见 main/master）
    for key in (
        "branch.main.remote",
        "branch.main.merge",
        "branch.master.remote",
        "branch.master.merge",
    ):
        r = _run(repo, ["config", "--local", "--unset", key], check=False)
        if r.returncode == 0:
            print(f"unset {key}")

    git_dir = repo / ".git"
    for path in (
        git_dir / "refs" / "remotes",
        git_dir / "logs" / "refs" / "remotes",
    ):
        if path.exists():
            shutil.rmtree(path)
            print(f"deleted {path.relative_to(repo)}")

    fetch_head = git_dir / "FETCH_HEAD"
    if fetch_head.exists():
        fetch_head.unlink()
        print("deleted .git/FETCH_HEAD")

    # 自检
    left = _run(repo, ["remote", "-v"], check=False).stdout.strip()
    if left:
        print("警告: 仍有 remote:\n" + left)
    else:
        print("OK: 本机已无 origin / remote，本地 commit 保留")


def cmd_add(repo: Path, url: str) -> None:
    if not (repo / ".git").is_dir():
        raise SystemExit(f"不是 git 仓库: {repo}")
    url = (url or "").strip()
    if not url:
        raise SystemExit("请提供 origin URL，例如 git@github.com:leiqiu666/quantus.git")

    existing = _run(repo, ["remote"], check=False).stdout.split()
    if "origin" in existing:
        _run(repo, ["remote", "remove", "origin"], check=False)
        print("removed existing origin")

    _run(repo, ["remote", "add", "origin", url])
    print(f"OK: origin -> {url}")
    print(_run(repo, ["remote", "-v"]).stdout.rstrip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="本机增加/清理 git origin（不影响远端仓库内容）"
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="仓库根目录（默认自动探测）",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    p_clean = sub.add_parser("clean", help="清理本机远端痕迹")
    p_clean.set_defaults(func=lambda ns: cmd_clean(ns.repo))

    p_add = sub.add_parser("add", help="添加 origin")
    p_add.add_argument("url", help="例如 git@github.com:leiqiu666/quantus.git")
    p_add.set_defaults(func=lambda ns: cmd_add(ns.repo, ns.url))

    ns = parser.parse_args(argv)
    ns.repo = (ns.repo or _git_root_default()).resolve()
    ns.func(ns)
    return 0


if __name__ == "__main__":
    sys.exit(main())
