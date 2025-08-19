# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "rich",
#     "typer",
# ]
# ///
from __future__ import annotations

import re
import subprocess
from typing import Annotated

import typer
from rich.console import Console

cli = typer.Typer()
console = Console()


def run(
    cmd: list[str],
    *,
    dry_run: bool = False,
    force_run: bool = False,
) -> str:
    command_str = " ".join(cmd)
    console.print(
        f"would run command: {command_str}"
        if dry_run and not force_run
        else f"running command: {command_str}"
    )

    if dry_run and not force_run:
        return ""

    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as e:
        console.print(f"[red]{cmd[0]} failed: {e.output}[/red]")
        raise typer.Exit(1) from e


@cli.command()
def release(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-d", help="Show commands without executing")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Skip safety checks")
    ] = False,
):
    current_branch = run(["git", "branch", "--show-current"], force_run=True).strip()
    if current_branch != "main" and not force:
        console.print(
            f"Must be on main branch to create release (currently on {current_branch})"
        )
        raise typer.Exit(1)

    if run(["git", "status", "--porcelain"], force_run=True) and not force:
        console.print("Working directory is not clean. Commit or stash changes first.")
        raise typer.Exit(1)

    run(["git", "fetch", "origin", "main"], dry_run=dry_run)
    local_sha = run(["git", "rev-parse", "@"], force_run=True).strip()
    remote_sha = run(["git", "rev-parse", "@{u}"], force_run=True).strip()
    if local_sha != remote_sha and not force:
        console.print("Local main is not up to date with remote. Pull changes first.")
        raise typer.Exit(1)

    log = run(["git", "log", "-1", "--pretty=format:%s"], force_run=True)

    # Try "bump version" pattern first
    if match := re.search(r"bump version .* -> ([\d.]+)", log):
        version = match.group(1)
    # Fall back to "release X.X.X" pattern
    elif match := re.search(r"release ([\d.]+)", log):
        version = match.group(1)
    else:
        console.print("Could not find version in latest commit message")
        raise typer.Exit(1)

    try:
        run(["gh", "release", "view", f"v{version}"], force_run=True)
        if not force:
            console.print(f"Release v{version} already exists!")
            raise typer.Exit(1)
    except Exception:
        pass

    if not force and not dry_run:
        typer.confirm(f"Create release v{version}?", abort=True)

    run(["gh", "release", "create", f"v{version}", "--generate-notes"], dry_run=dry_run)


if __name__ == "__main__":
    cli()
