"""数据实体表结构同步 CLI

提供「同步全部表结构」等功能，遍历 data_entities 目录下的所有实体文件，
依次调用 sync_table 创建或更新数据库表。

用法:
    uv run python -m src.entities.data_entities.cli            # 交互式菜单
    uv run python -m src.entities.data_entities.cli sync-all   # 直接执行
"""

import typer
from typing import Callable

import questionary
from questionary import Choice

from src.common.database import sync_table
from src.entities.data_entities.registry import ALL_ENTITIES

# create typer app
app = typer.Typer()

_MENU_ROWS: list[tuple[str, str]] = [
    ("同步全量表结构 (sync-all)", "sync-all"),
]


def _run_interactive_menu() -> None:
    choices: list[Choice[str | None]] = [
        Choice(title=label, value=key) for label, key in _MENU_ROWS
    ]
    choices.append(Choice(title="退出", value=None))

    picked = questionary.select(
        "选择要执行的任务（↑↓ 移动，Enter 确认）:",
        choices=choices,
        qmark=">",
    ).ask()

    if picked is None:
        return
    handler = _MENU_HANDLERS.get(picked)
    if handler is None:
        typer.echo(f"[错误] 未注册菜单项: {picked}", err=True)
        raise typer.Exit(1)
    handler()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return
    _run_interactive_menu()
    raise typer.Exit(0)


@app.command("sync-all")
def sync_all():
    """同步全部表结构（创建或更新所有实体对应的数据库表）"""
    typer.echo("=" * 60)
    typer.echo(f"即将同步 {len(ALL_ENTITIES)} 张表的结构")
    typer.echo("=" * 60)

    # 展示将要同步的表
    for i, entity in enumerate(ALL_ENTITIES, 1):
        table_name = entity.__tablename__
        col_count = len(entity.__table__.columns)
        typer.echo(f"  {i}. {table_name:30s} ({col_count} 个字段)")

    typer.echo("")

    success_count = 0
    fail_count = 0

    for entity in ALL_ENTITIES:
        table_name = entity.__tablename__
        typer.echo(f"\n{'─' * 60}")
        typer.echo(f"正在同步表: {table_name}")
        typer.echo(f"{'─' * 60}")

        try:
            # interactive=False: 自动确认，不再手动输入 yes
            sync_table(entity, interactive=False)
            success_count += 1
        except Exception as e:
            typer.echo(f"[错误] 同步表 {table_name} 失败: {e}", err=True)
            fail_count += 1

    # 汇总
    typer.echo(f"\n{'=' * 60}")
    typer.echo(f"同步完成！成功: {success_count}, 失败: {fail_count}")
    typer.echo(f"{'=' * 60}")

    if fail_count > 0:
        raise typer.Exit(code=1)


# 菜单 key -> 执行函数（须在上方命令函数定义之后，才能绑定同一实现）
_MENU_HANDLERS: dict[str, Callable[[], None]] = {
    "sync-all": sync_all,
}

# start the app
if __name__ == "__main__":
    app()
