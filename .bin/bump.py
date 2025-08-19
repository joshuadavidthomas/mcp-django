# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "bumpver",
#     "rich",
#     "typer",
# ]
# ///
from __future__ import annotations

import re
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

cli = typer.Typer()
console = Console()


class Version(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


class Tag(str, Enum):
    DEV = "dev"
    ALPHA = "alpha"
    BETA = "beta"
    RC = "rc"
    FINAL = "final"


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
        console.print(f"[red]{cmd[0]} failed: {e.output}[/red]", file=sys.stderr)
        raise typer.Exit(1) from e


def get_new_version(version: Version, tag: Tag | None = None) -> str:
    cmd = ["bumpver", "update", "--dry", f"--{version}"]
    if tag:
        cmd.extend(["--tag", tag])
    output = run(cmd, force_run=True)

    if match := re.search(r"New Version: (.+)", output):
        return match.group(1)
    return typer.prompt("Failed to get new version. Enter manually")


def update_changelog(new_version: str, dry_run: bool = False) -> None:
    repo_url = (
        run(["git", "remote", "get-url", "origin"], force_run=True)
        .strip()
        .replace(". git", "")
    )
    changelog = Path("CHANGELOG.md")
    content = changelog.read_text()

    content = re.sub(
        r"## \[Unreleased\]",
        f"## [{new_version}]",
        content,
        count=1,
    )
    content = re.sub(
        rf"## \[{new_version}\]",
        f"## [Unreleased]\n\n## [{new_version}]",
        content,
        count=1,
    )
    content += f"[{new_version}]: {repo_url}/releases/tag/v{new_version}\n"
    content = re.sub(
        r"\[unreleased\]: .*\n",
        f"[unreleased]: {repo_url}/compare/v{new_version}...HEAD\n",
        content,
        count=1,
    )

    changelog.write_text(content)
    run(["git", "add", "."], dry_run=dry_run)
    run(
        ["git", "commit", "-m", f"update CHANGELOG for version {new_version}"],
        dry_run=dry_run,
    )


def update_uv_lock(new_version: str, dry_run: bool = False) -> None:
    run(["uv", "lock"], dry_run=dry_run)

    changes = run(["git", "status", "--porcelain"], force_run=True)
    if "uv.lock" not in changes:
        console.print("No changes to uv.lock, skipping commit")
        return

    run(["git", "add", "uv.lock"], dry_run=dry_run)
    run(
        ["git", "commit", "-m", f"update uv.lock for version {new_version}"],
        dry_run=dry_run,
    )


@cli.command()
def version(
    version: Annotated[
        Version,
        typer.Option("--version", "-v", help="The tag to add to the new version"),
    ],
    tag: Annotated[
        Tag, typer.Option("--tag", "-t", help="The tag to add to the new version")
    ]
    | None = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-d", help="Show commands without executing")
    ] = False,
):
    # get changes for PR message
    tags = run(["git", "tag", "--sort=-creatordate"], force_run=True).splitlines()
    changes = run(
        [
            "git",
            "log",
            f"{tags[0] if tags else ''}..HEAD",
            "--pretty=format:- `%h`: %s",
            "--reverse",
        ],
        force_run=True,
    )

    # get new version
    new_version = get_new_version(version, tag)

    # checkout release branch
    release_branch = f"release-v{new_version}"
    try:
        run(["git", "checkout", "-b", release_branch], dry_run=dry_run)
    except Exception:
        run(["git", "checkout", release_branch], dry_run=dry_run)

    # bump the version
    cmd = ["bumpver", "update", f"--{version}"]
    if tag:
        cmd.extend(["--tag", tag])
    run(cmd, dry_run=dry_run)

    # get bumpver commit message for PR title
    title = run(["git", "log", "-1", "--pretty=%s"], force_run=True)

    # update ancillary release files
    update_changelog(new_version, dry_run)
    update_uv_lock(new_version, dry_run)

    # push and create PR
    run(["git", "push", "--set-upstream", "origin", release_branch], dry_run=dry_run)
    run(
        [
            "gh",
            "pr",
            "create",
            "--base",
            "main",
            "--head",
            release_branch,
            "--title",
            title,
            "--body",
            changes,
        ],
        dry_run=dry_run,
    )


if __name__ == "__main__":
    cli()
