# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "rich",
#     "typer",
#     "tomli",
# ]
# ///
from __future__ import annotations

import re
import subprocess
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Annotated
from typing import override

import tomli
import typer
from rich.console import Console

cli = typer.Typer()
console = Console()


class StrEnum(str, Enum):
    @override
    def __format__(self, format_spec: str) -> str:
        return format(self.value, format_spec)


class Version(StrEnum):
    MAJOR = "major"
    MINOR = "minor"
    PATCH = "patch"


def run(
    cmd: list[str],
    *,
    dry_run: bool = False,
    force_run: bool = False,
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
        console.print(f"[red]{cmd[0]} failed: {e.output}[/red]")
        raise typer.Exit(1) from e


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


def get_current_version(package: str | None = None) -> str:
    """Get current version of a package."""
    if package:
        pyproject_path = Path(f"packages/{package}/pyproject.toml")
    else:
        pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        console.print(f"[red]pyproject.toml not found: {pyproject_path}[/red]")
        raise typer.Exit(1)

    with open(pyproject_path, "rb") as f:
        data = tomli.load(f)

    return data["project"]["version"]


def get_new_version(version: Version, package: str | None = None) -> tuple[str, str]:
    """Get the new version after bump. Returns (current, new) tuple."""
    cmd = ["uv", "version", "--bump", version.value]
    if package:
        cmd.extend(["--package", package])

    output = run(cmd + ["--dry-run"], force_run=True)

    # Parse output like "mcp-django 0.1.0 => 0.2.0" or "0.1.0 => 0.2.0"
    if match := re.search(r"([\d.]+(?:[-.\w]*)?)\s*=>\s*([\d.]+(?:[-.\w]*)?)", output):
        return match.group(1), match.group(2)

    # Fallback: get current version and prompt for new
    current = get_current_version(package)
    new = typer.prompt(
        f"Failed to parse new version. Current is {current}. Enter new version"
    )
    return current, new


def get_next_calver() -> str:
    """Generate next CalVer tag in YYYY.M.INCR format."""
    today = date.today()
    prefix = f"{today.year}.{today.month}"  # No zero-padding

    # Check CHANGELOG for existing CalVer tags from this month
    changelog_path = Path("CHANGELOG.md")
    if not changelog_path.exists():
        return f"{prefix}.1"

    content = changelog_path.read_text()

    # Find all CalVer tags matching this month's prefix
    # Pattern: ## [YYYY.MM.N]
    existing = re.findall(rf"## \[{re.escape(prefix)}\.(\d+)\]", content)

    if existing:
        # Find highest increment and add 1
        next_incr = max(int(i) for i in existing) + 1
    else:
        next_incr = 1

    return f"{prefix}.{next_incr}"


def update_changelog(bumps: list[tuple[str, str, str]], dry_run: bool = False) -> str:
    """Update CHANGELOG for version bumps and convert to CalVer.

    Args:
        bumps: List of (package_name, old_version, new_version) tuples.
               Use "root" for the root package.

    Returns:
        The CalVer tag that was created
    """
    changelog = Path("CHANGELOG.md")
    if not changelog.exists():
        console.print("[yellow]CHANGELOG.md not found, skipping update[/yellow]")
        return ""

    content = changelog.read_text()

    # Generate CalVer tag
    calver = get_next_calver()
    console.print(f"[bold]CalVer release:[/bold] {calver}")

    if "## [Unreleased]" not in content:
        console.print("[yellow]Could not find '## [Unreleased]' in CHANGELOG[/yellow]")
        return ""

    # Find everything under [Unreleased] until the next ## heading
    unreleased_match = re.search(
        r"(## \[Unreleased\])(.*?)((?=\n## )|$)", content, re.DOTALL
    )

    if not unreleased_match:
        console.print("[yellow]Could not parse Unreleased section[/yellow]")
        return ""

    unreleased_content = unreleased_match.group(2).strip()

    # Build version list entries
    version_entries = []
    for pkg_name, old_ver, new_ver in bumps:
        if pkg_name == "root":
            version_entries.append(f"- mcp-django: {new_ver}")
        else:
            version_entries.append(f"- {pkg_name}: {new_ver}")

    # Build the new CalVer section with existing content
    calver_section = f"## [{calver}]\n\n"
    if version_entries:
        calver_section += "\n".join(version_entries) + "\n"

    # Add any existing content from Unreleased (but skip if it's just version entries)
    if unreleased_content and not all(
        line.strip().startswith("- mcp-django") or line.strip() == ""
        for line in unreleased_content.split("\n")
    ):
        if version_entries:
            calver_section += "\n"
        calver_section += unreleased_content

    # Replace [Unreleased] with new [Unreleased] and [CalVer] sections
    new_content = content.replace(
        unreleased_match.group(0),
        f"## [Unreleased]\n\n{calver_section}{unreleased_match.group(3)}",
    )

    # Update the link references at the bottom
    # Add new CalVer link and update unreleased comparison
    if "[unreleased]:" in new_content:
        # Update unreleased link to compare from new CalVer tag
        new_content = re.sub(
            r"\[unreleased\]: (.+?)/compare/(.+?)\.\.\.HEAD",
            rf"[unreleased]: \1/compare/{calver}...HEAD",
            new_content,
            count=1,
        )

        # Add the CalVer release link
        # Find the position right after the unreleased link
        unreleased_link_match = re.search(r"(\[unreleased\]: .+?\n)", new_content)
        if unreleased_link_match:
            insert_pos = unreleased_link_match.end()
            repo_match = re.search(r"\[unreleased\]: (.+?)/compare", new_content)
            if repo_match:
                repo_url = repo_match.group(1)
                calver_link = f"[{calver}]: {repo_url}/releases/tag/{calver}\n"
                new_content = (
                    new_content[:insert_pos] + calver_link + new_content[insert_pos:]
                )

    if not dry_run:
        changelog.write_text(new_content)
        console.print(
            f"[green]Updated CHANGELOG.md with CalVer release {calver}[/green]"
        )

    return calver


def update_uv_lock(dry_run: bool = False) -> None:
    """Update uv.lock file."""
    run(["uv", "lock"], dry_run=dry_run)

    changes = run(["git", "status", "--porcelain"], force_run=True)
    if "uv.lock" not in changes:
        console.print("[dim]No changes to uv.lock[/dim]")
        return

    console.print("[green]Updated uv.lock[/green]")


def write_version_file(calver: str, dry_run: bool = False) -> None:
    """Write CalVer to .github/VERSION file."""
    version_file = Path(".github/VERSION")

    if not dry_run:
        version_file.parent.mkdir(parents=True, exist_ok=True)
        version_file.write_text(f"{calver}\n")
        console.print(f"[green]Wrote CalVer {calver} to .github/VERSION[/green]")
    else:
        console.print(f"[dim]Would write CalVer {calver} to .github/VERSION[/dim]")


@cli.command()
def bump(
    version: Annotated[
        Version, typer.Argument(help="Version component to bump (major/minor/patch)")
    ],
    packages: Annotated[
        list[str] | None,
        typer.Option(
            "--package",
            "-p",
            help="Package(s) to bump. Can be specified multiple times.",
        ),
    ] = None,
    all_packages: Annotated[
        bool, typer.Option("--all", "-a", help="Bump all packages including root")
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", "-d", help="Show what would be done without executing"
        ),
    ] = False,
    changelog: Annotated[
        bool, typer.Option("--changelog/--no-changelog", help="Update CHANGELOG.md")
    ] = True,
    lock: Annotated[
        bool, typer.Option("--lock/--no-lock", help="Update uv.lock")
    ] = True,
):
    """Bump version(s) for workspace packages.

    Examples:
        bump.py minor                    # Bump root package
        bump.py patch -p mcp-django-shell  # Bump specific package
        bump.py minor -p mcp-django-shell -p mcp-django-crud  # Multiple packages
        bump.py major --all              # Bump everything
    """

    # Check for uncommitted changes
    if not dry_run:
        status = run(["git", "status", "--porcelain"], force_run=True)
        if status:
            console.print("[red]Error: You have uncommitted changes.[/red]")
            console.print("Please commit or stash them before bumping versions.")
            console.print("\n[dim]Uncommitted files:[/dim]")
            console.print(status)
            raise typer.Exit(1)

    # Determine what to bump
    bumps_to_make = []

    if all_packages:
        # Bump root and all workspace packages
        console.print("[bold]Bumping all packages[/bold]")

        # Root package
        current, new = get_new_version(version, None)
        bumps_to_make.append(("root", current, new))

        # All workspace packages
        for pkg in get_workspace_packages():
            current, new = get_new_version(version, pkg)
            bumps_to_make.append((pkg, current, new))

    elif packages:
        # Bump specific packages
        for pkg in packages:
            # Validate package exists
            if pkg != "root" and pkg not in get_workspace_packages():
                console.print(f"[red]Package not found: {pkg}[/red]")
                console.print(
                    f"Available packages: {', '.join(get_workspace_packages())}"
                )
                raise typer.Exit(1)

            if pkg == "root":
                current, new = get_new_version(version, None)
            else:
                current, new = get_new_version(version, pkg)
            bumps_to_make.append((pkg, current, new))

    else:
        # Default: bump root package only
        current, new = get_new_version(version, None)
        bumps_to_make.append(("root", current, new))

    # Display what will be bumped
    console.print("\n[bold]Version bumps:[/bold]")
    for pkg_name, current_ver, new_ver in bumps_to_make:
        display_name = "mcp-django" if pkg_name == "root" else pkg_name
        console.print(
            f"  {display_name}: [cyan]{current_ver}[/cyan] → [green]{new_ver}[/green]"
        )

    if not dry_run and not typer.confirm("\nProceed with these bumps?"):
        raise typer.Abort()

    # Generate CalVer early to use in branch name
    calver_tag = get_next_calver() if changelog else ""

    # Create release branch
    if calver_tag and not dry_run:
        branch_name = f"release-v{calver_tag}"
        console.print(f"\n[bold]Creating release branch:[/bold] {branch_name}")
        run(["git", "checkout", "-b", branch_name], dry_run=dry_run)

    # Execute the bumps
    console.print("\n[bold]Executing version bumps...[/bold]")
    for pkg_name, _, _ in bumps_to_make:
        if pkg_name == "root":
            run(["uv", "version", "--bump", version.value], dry_run=dry_run)
        else:
            run(
                ["uv", "version", "--package", pkg_name, "--bump", version.value],
                dry_run=dry_run,
            )

    # Update ancillary files
    if changelog:
        console.print("\n[bold]Updating CHANGELOG...[/bold]")
        # Pass the already-generated calver_tag to update_changelog
        updated_calver = update_changelog(bumps_to_make, dry_run)
        # Verify it matches what we expected
        if updated_calver != calver_tag:
            console.print(
                f"[yellow]Warning: CalVer mismatch - expected {calver_tag}, got {updated_calver}[/yellow]"
            )

        # Write VERSION file with CalVer
        if calver_tag:
            write_version_file(calver_tag, dry_run)

    if lock:
        console.print("\n[bold]Updating uv.lock...[/bold]")
        update_uv_lock(dry_run)

    # Git operations
    if not dry_run:
        console.print("\n[bold]Creating git commit...[/bold]")

        # Stage only the files we changed
        files_to_add = []

        # Add root pyproject.toml if it exists and was potentially modified
        if Path("pyproject.toml").exists():
            files_to_add.append("pyproject.toml")

        # Add package pyproject.toml files that were bumped
        for pkg_name, _, _ in bumps_to_make:
            if pkg_name != "root":
                pkg_file = f"packages/{pkg_name}/pyproject.toml"
                if Path(pkg_file).exists():
                    files_to_add.append(pkg_file)

        # Add CHANGELOG if it was updated
        if changelog and Path("CHANGELOG.md").exists():
            files_to_add.append("CHANGELOG.md")

        # Add VERSION file if it was created
        if calver_tag and Path(".github/VERSION").exists():
            files_to_add.append(".github/VERSION")

        # Only add uv.lock if it exists AND is not ignored
        if lock and Path("uv.lock").exists():
            # Check if uv.lock is tracked by git
            result = run(["git", "ls-files", "uv.lock"], force_run=True)
            if result:  # File is tracked
                files_to_add.append("uv.lock")

        # Stage the specific files
        if files_to_add:
            run(["git", "add"] + files_to_add, dry_run=dry_run)
        else:
            console.print("[yellow]No files to stage[/yellow]")

        # Create commit message
        if len(bumps_to_make) == 1:
            pkg_name, old_ver, new_ver = bumps_to_make[0]
            display_name = "mcp-django" if pkg_name == "root" else pkg_name
            commit_msg = f"bump {display_name} version {old_ver} → {new_ver}"
        else:
            pkg_list = ", ".join(
                "mcp-django" if p == "root" else p for p, _, _ in bumps_to_make
            )
            commit_msg = f"bump versions for {pkg_list}"

        # Add CalVer to commit message if we have one
        if calver_tag:
            commit_msg = f":bookmark: release {calver_tag}: {commit_msg}"
        else:
            commit_msg = f":bookmark: {commit_msg}"

        run(["git", "commit", "-m", commit_msg], dry_run=dry_run)

        console.print(f"\n[green]✓ Committed:[/green] {commit_msg}")

    console.print("\n[bold green]Version bump complete![/bold green]")
    if calver_tag:
        console.print(f"[bold yellow]Release prepared:[/bold yellow] {calver_tag}")

    if not dry_run:
        console.print("\n[dim]Next steps:[/dim]")
        console.print("  1. Review the changes: [cyan]git diff HEAD~1[/cyan]")
        if calver_tag:
            console.print(
                f"  2. Push the release branch: [cyan]git push -u origin release-v{calver_tag}[/cyan]"
            )
            console.print("  3. Create a PR from the release branch to main")
            console.print(
                "  4. After PR is merged, run release script: [cyan].bin/release.py[/cyan]"
            )
        else:
            console.print("  2. Push to remote: [cyan]git push[/cyan]")
            console.print("  3. Create a PR or merge to main")


if __name__ == "__main__":
    cli()
