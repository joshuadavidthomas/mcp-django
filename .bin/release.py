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
from pathlib import Path
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


def get_calver() -> str:
    """Read CalVer version from .github/VERSION file."""
    version_file = Path(".github/VERSION")
    if not version_file.exists():
        console.print("[red]No .github/VERSION file found. Run bump.py first.[/red]")
        raise typer.Exit(1)

    calver = version_file.read_text().strip()
    console.print(f"[dim]Found CalVer: {calver}[/dim]")
    return calver


def get_package_version() -> str:
    """Get current version of mcp-django using uv."""
    console.print("[dim]Getting package version...[/dim]")
    output = run(["uv", "version"], force_run=True)
    # Parse output like "mcp-django 0.2.0" or just "0.2.0"
    if match := re.search(r"(?:mcp-django\s+)?([\d.]+(?:[-.\w]*)?)", output):
        version = match.group(1)
        console.print(f"  mcp-django: {version}")
        return version

    console.print("[red]Failed to parse version from uv output[/red]")
    raise typer.Exit(1)


@cli.command()
def release(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-d", help="Show commands without executing")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", "-f", help="Skip safety checks")
    ] = False,
):
    """Create a new release with CalVer and package-specific tags."""

    # Safety checks
    current_branch = run(["git", "branch", "--show-current"], force_run=True).strip()
    if current_branch != "main" and not force:
        console.print(
            f"[red]Must be on main branch to create release (currently on {current_branch})[/red]"
        )
        raise typer.Exit(1)

    if run(["git", "status", "--porcelain"], force_run=True) and not force:
        console.print(
            "[red]Working directory is not clean. Commit or stash changes first.[/red]"
        )
        raise typer.Exit(1)

    run(["git", "fetch", "origin", "main"], dry_run=dry_run)
    local_sha = run(["git", "rev-parse", "@"], force_run=True).strip()
    remote_sha = run(["git", "rev-parse", "@{u}"], force_run=True).strip()
    if local_sha != remote_sha and not force:
        console.print(
            "[red]Local main is not up to date with remote. Pull changes first.[/red]"
        )
        raise typer.Exit(1)

    # Get CalVer from VERSION file
    calver = get_calver()

    # Check if CalVer release already exists (with v prefix)
    calver_tag = f"v{calver}"
    try:
        run(["gh", "release", "view", calver_tag], force_run=True)
        if not force:
            console.print(f"[red]Release {calver_tag} already exists![/red]")
            raise typer.Exit(1)
    except Exception:
        pass  # Release doesn't exist, good to proceed

    # Get current package version
    version = get_package_version()

    # Show what we're about to release
    console.print(f"\n[bold]Creating release {calver}[/bold]")
    console.print(f"  [cyan]mcp-django:[/cyan] {version}")

    # Confirm with user
    if not force and not dry_run:
        typer.confirm("\nProceed with release?", abort=True)

    # Create tags
    console.print("\n[bold]Creating tags...[/bold]")
    tags = []

    # CalVer tag with v prefix
    calver_tag = f"v{calver}"
    tags.append(calver_tag)
    console.print(f"  [green]✓[/green] {calver_tag}")

    # Package-specific tag
    package_tag = f"mcp-django-v{version}"
    tags.append(package_tag)
    console.print(f"  [green]✓[/green] {package_tag}")

    # Create all tags locally
    for tag in tags:
        run(["git", "tag", tag], dry_run=dry_run)

    # Push all tags at once
    console.print("\n[bold]Pushing tags to origin...[/bold]")
    run(["git", "push", "origin"] + tags, dry_run=dry_run)

    # Create GitHub release with CalVer tag
    console.print(f"\n[bold]Creating GitHub release {calver_tag}...[/bold]")
    run(["gh", "release", "create", calver_tag, "--generate-notes"], dry_run=dry_run)

    # Success message
    console.print(f"\n[bold green]✓ Released {calver_tag}![/bold green]")
    console.print(
        "\n[dim]The CI/CD pipeline will now build and publish packages to PyPI.[/dim]"
    )


if __name__ == "__main__":
    cli()
