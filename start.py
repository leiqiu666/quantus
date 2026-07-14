#!/usr/bin/env python3
"""开发态一键启动：默认拉起 API + Admin；可扩展其它常驻进程。

用法：
  uv run ./start.py                  # api + admin（调度随 api 内嵌）
  uv run ./start.py --only api
  uv run ./start.py --only admin
  uv run ./start.py --standalone-scheduler  # api 关闭内嵌调度，另起 quantus-scheduler
  uv run ./start.py --list
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ADMIN_DIR = ROOT / "src" / "web" / "admin"


def _resolve_cmd(cmd: list[str]) -> list[str]:
    """Resolve argv[0] so Windows .cmd shims (pnpm/npm/uv) work without shell=True."""
    if not cmd:
        return cmd
    exe = shutil.which(cmd[0])
    if exe is None:
        return cmd
    # CreateProcess cannot run .cmd/.bat directly; wrap with cmd /c
    if sys.platform == "win32" and exe.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", exe, *cmd[1:]]
    return [exe, *cmd[1:]]


@dataclass(frozen=True)
class Service:
    name: str
    title: str
    cmd: list[str]
    cwd: Path = ROOT
    default: bool = True
    url: str | None = None
    env: dict[str, str] = field(default_factory=dict)
    note: str | None = None


SERVICES: dict[str, Service] = {
    "api": Service(
        name="api",
        title="HTTP API",
        cmd=[
            "uv",
            "run",
            "uvicorn",
            "src.api.main:app",
            "--reload",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
        url="http://localhost:8000/docs",
        env={"SCHEDULER_EMBEDDED_IN_API": "true"},
        note="调度默认随 API 内嵌（SCHEDULER_ENABLED=true）",
    ),
    "admin": Service(
        name="admin",
        title="Admin (Vite)",
        cmd=["pnpm", "dev"],
        cwd=ADMIN_DIR,
        url="http://localhost:5173",
        # 无 TTY 时 pnpm 会因 modules 校验弹确认而失败；禁止 corepack 改 package.json
        env={
            "CI": "true",
            "COREPACK_ENABLE_AUTO_PIN": "0",
        },
    ),
    "scheduler": Service(
        name="scheduler",
        title="Scheduler Worker",
        cmd=["uv", "run", "quantus-scheduler"],
        default=False,
        note="仅 --standalone-scheduler；与 API 内嵌互斥",
    ),
}


def _list_services() -> None:
    print("可启动服务（未来在 SERVICES 注册即可）：")
    for svc in SERVICES.values():
        flag = "默认开" if svc.default else "可选"
        extra = f"  {svc.url}" if svc.url else ""
        note = f"  # {svc.note}" if svc.note else ""
        print(f"  {svc.name:12} [{flag}]  {svc.title}{extra}{note}")


def _pipe_output(proc: subprocess.Popen[str], prefix: str) -> None:
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(f"[{prefix}] {line}")
        sys.stdout.flush()


def _start(svc: Service, extra_env: dict[str, str] | None = None) -> subprocess.Popen[str]:
    env = os.environ.copy()
    # Windows 控制台默认 GBK；统一子进程 UTF-8，避免中文异常信息乱码
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.update(svc.env)
    if extra_env:
        env.update(extra_env)
    argv = _resolve_cmd(svc.cmd)
    print(f"→ 启动 {svc.title} ({svc.name}): {' '.join(svc.cmd)}")
    if svc.url:
        print(f"  {svc.url}")
    return subprocess.Popen(
        argv,
        cwd=str(svc.cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Quantus 开发态一键启动")
    parser.add_argument(
        "--only",
        metavar="NAME",
        help="只启动指定服务，逗号分隔（如 api,admin）",
    )
    parser.add_argument(
        "--standalone-scheduler",
        action="store_true",
        help="关闭 API 内嵌调度，另起独立 quantus-scheduler",
    )
    parser.add_argument("--list", action="store_true", help="列出可启动服务")
    args = parser.parse_args()

    if args.list:
        _list_services()
        return 0

    if args.only:
        names = [n.strip() for n in args.only.split(",") if n.strip()]
        unknown = [n for n in names if n not in SERVICES]
        if unknown:
            print(f"未知服务: {', '.join(unknown)}", file=sys.stderr)
            _list_services()
            return 2
    else:
        names = [n for n, s in SERVICES.items() if s.default]

    if args.standalone_scheduler:
        if "scheduler" not in names:
            names.append("scheduler")
        if "api" not in names:
            print("提示: --standalone-scheduler 建议同时启动 api（当前未包含）")

    procs: list[tuple[Service, subprocess.Popen[str]]] = []
    stop = False

    def _shutdown(*_args: object) -> None:
        nonlocal stop
        if stop:
            return
        stop = True
        print("\n正在停止全部子进程…")
        for _, p in procs:
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    for name in names:
        svc = SERVICES[name]
        extra: dict[str, str] | None = None
        if name == "api" and args.standalone_scheduler:
            # 与独立 Worker 互斥：关掉 API 内嵌调度
            extra = {
                "SCHEDULER_ENABLED": "false",
                "SCHEDULER_EMBEDDED_IN_API": "false",
            }
            print("  API 将以 SCHEDULER_ENABLED=false 启动（独立 scheduler）")
        if name == "scheduler" and not args.standalone_scheduler and "api" in names:
            print("跳过 scheduler：默认随 API 内嵌；需要时加 --standalone-scheduler")
            continue
        if name == "admin" and not ADMIN_DIR.is_dir():
            print(f"Admin 目录不存在: {ADMIN_DIR}", file=sys.stderr)
            _shutdown()
            return 1
        try:
            proc = _start(svc, extra)
        except FileNotFoundError as e:
            print(f"启动失败 {svc.name}: {e}", file=sys.stderr)
            _shutdown()
            return 1
        procs.append((svc, proc))
        threading.Thread(target=_pipe_output, args=(proc, svc.name), daemon=True).start()

    if not procs:
        print("没有要启动的服务", file=sys.stderr)
        return 1

    print("全部已拉起，Ctrl+C 结束。")
    alive = {id(p): True for _, p in procs}
    while not stop and any(alive.values()):
        for svc, p in procs:
            if not alive.get(id(p)):
                continue
            code = p.poll()
            if code is not None:
                alive[id(p)] = False
                print(f"[{svc.name}] 已退出 (code={code})")
        time.sleep(0.3)

    deadline = time.time() + 8
    for _, p in procs:
        while p.poll() is None and time.time() < deadline:
            time.sleep(0.1)
        if p.poll() is None:
            p.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
