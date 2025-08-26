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
    check: bool = True,
) -> str:
    command_str = " ".join(cmd)
    console.print(
        f"[dim]would run:[/dim] {command_str}"
        if dry_run and not force_run
        else f"[dim]running:[/dim] {command_str}"
    )

    if dry_run and not force_run:
        return ""

    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()
    except subprocess.CalledProcessError as e:
        if check:
            console.print(f"[red]{cmd[0]} failed: {e.output}[/red]")
            raise typer.Exit(1) from e
        return ""


def get_calver() -> str:
    """Read CalVer version from .github/VERSION file."""
    version_file = Path(".github/VERSION")
    if not version_file.exists():
        console.print("[red]No .github/VERSION file found. Run bump.py first.[/red]")
        raise typer.Exit(1)

    calver = version_file.read_text().strip()
    console.print(f"[cyan]Found CalVer: {calver}[/cyan]")
    return calver


def get_workspace_packages() -> list[str]:
    """Get list of workspace packages from packages/ directory."""
    packages_dir = Path("packages")
    if not packages_dir.exists():
        return []

    packages = []
    for pkg_dir in packages_dir.iterdir():
        if pkg_dir.is_dir() and (pkg_dir / "pyproject.toml").exists():
            packages.append(pkg_dir.name)
    return sorted(packages)


def get_package_versions() -> dict[str, str]:
    """Get current versions of all packages using uv."""
    packages = {}

    # Get root package version
    output = run(["uv", "version"], force_run=True)
    if match := re.search(r"([\d.]+(?:[-.\w]*)?)", output):
        packages["mcp-django"] = match.group(1)

    # Get workspace package versions
    for package in get_workspace_packages():
        output = run(["uv", "version", "--package", package], force_run=True)
        if match := re.search(r"([\d.]+(?:[-.\w]*)?)", output):
            packages[package] = match.group(1)

    return packages


def create_and_push_tags(
    calver: str,
    packages: dict[str, str],
    dry_run: bool = False,
    force: bool = False,
) -> list[str]:
    """Create and push git tags for CalVer and all packages."""
    tags = []

    # Create CalVer tag
    tags.append(calver)

    # Create package-specific tags
    for package, version in packages.items():
        tag = f"{package}-v{version}"
        tags.append(tag)

    # Check if any tags already exist
    existing_tags = []
    for tag in tags:
        result = run(["git", "tag", "-l", tag], force_run=True)
        if result:
            existing_tags.append(tag)

    if existing_tags and not force:
        console.print("[red]The following tags already exist:[/red]")
        for tag in existing_tags:
            console.print(f"  - {tag}")
        console.print("[yellow]Use --force to overwrite existing tags[/yellow]")
        raise typer.Exit(1)

    # Create tags (with force if needed)
    for tag in tags:
        tag_cmd = ["git", "tag", tag]
        if force and tag in existing_tags:
            tag_cmd.insert(2, "-f")  # git tag -f <tag>
        run(tag_cmd, dry_run=dry_run)
        console.print(f"[green]Created tag:[/green] {tag}")

    # Push all tags at once
    push_cmd = ["git", "push", "origin"] + tags
    if force:
        push_cmd.insert(2, "-f")  # git push -f origin ...
    run(push_cmd, dry_run=dry_run)
    console.print(f"[green]Pushed {len(tags)} tags to origin[/green]")

    return tags


@cli.command()
def release(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-d", help="Show commands without executing")
    ] = False,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Skip safety checks and overwrite existing tags/releases",
        ),
    ] = False,
):
    """Create a new release from the current CalVer and package versions."""

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

    # Fetch latest from remote
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

    # Get current package versions from uv
    packages = get_package_versions()

    # Check if GitHub release already exists
    existing_release = run(
        ["gh", "release", "view", calver], force_run=True, check=False
    )
    if existing_release and not force:
        console.print(f"[red]GitHub release {calver} already exists![/red]")
        console.print("[yellow]Use --force to recreate the release[/yellow]")
        raise typer.Exit(1)

    # Display what we're about to release
    console.print(f"\n[bold]Creating release {calver}[/bold]")
    console.print("[dim]Package versions:[/dim]")
    for package, version in packages.items():
        console.print(f"  - {package}: {version}")

    # Confirm with user
    if not force and not dry_run:
        if not typer.confirm("\nProceed with release?"):
            raise typer.Abort()

    # Create and push tags
    console.print("\n[bold]Creating and pushing tags...[/bold]")
    tags = create_and_push_tags(calver, packages, dry_run, force)

    # Delete existing GitHub release if force flag is set
    if existing_release and force:
        console.print(f"[yellow]Deleting existing release {calver}...[/yellow]")
        run(["gh", "release", "delete", calver, "--yes"], dry_run=dry_run)

    # Create GitHub release with CalVer tag
    console.print(f"\n[bold]Creating GitHub release...[/bold]")
    run(["gh", "release", "create", calver, "--generate-notes"], dry_run=dry_run)

    # Success message
    console.print(f"\n[bold green]✓ Released {calver}![/bold green]")
    console.print(f"[dim]Created {len(tags)} tags:[/dim]")
    for tag in tags:
        console.print(f"  - {tag}")

    console.print(
        f"\n[dim]View release: https://github.com/joshuadavidthomas/mcp-django/releases/tag/{calver}[/dim]"
    )


if __name__ == "__main__":
    cli()
