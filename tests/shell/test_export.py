from __future__ import annotations

import os
from pathlib import Path

import pytest

from mcp_django.shell.code import parse_code
from mcp_django.shell.core import DjangoShell


@pytest.fixture
def shell():
    shell = DjangoShell()
    yield shell
    shell.clear_history()


class TestExportHistory:
    def test_export_empty_history(self, shell):
        """Export with no history returns empty comment."""
        result = shell.export_history()
        assert "No history" in result

    def test_export_basic_code(self, shell):
        """Export basic execution to script."""
        parsed_code, setup, code_type = parse_code("2 + 2")
        shell._execute(parsed_code, setup, code_type)

        script = shell.export_history()

        assert "# Django Shell Session Export" in script
        assert "# Step 1" in script
        assert "2 + 2" in script

    def test_export_excludes_output(self, shell):
        """Export does not include execution results."""
        parsed_code, setup, code_type = parse_code("2 + 2")
        shell._execute(parsed_code, setup, code_type)

        script = shell.export_history()

        assert "# → 4" not in script
        assert "2 + 2" in script

    def test_export_excludes_errors_by_default(self, shell):
        """Export excludes error results by default."""
        parsed_code, setup, code_type = parse_code("1 / 0")
        shell._execute(parsed_code, setup, code_type)

        script = shell.export_history(include_errors=False)

        # Should have header but no steps
        assert "# Django Shell Session Export" in script
        assert "1 / 0" not in script

    def test_export_includes_errors_when_requested(self, shell):
        """Export includes error code when include_errors=True."""
        parsed_code, setup, code_type = parse_code("1 / 0")
        shell._execute(parsed_code, setup, code_type)

        script = shell.export_history(include_errors=True)

        assert "1 / 0" in script
        # Error messages are not included in output
        assert "# → Error:" not in script

    def test_export_deduplicates_imports(self, shell):
        """Export always consolidates imports at the top."""
        # Execute code with same import twice (without DB access)
        code1 = "from datetime import datetime\nx = datetime.now()"
        parsed_code, setup, code_type = parse_code(code1)
        shell._execute(parsed_code, setup, code_type)

        code2 = "from datetime import datetime\ny = datetime.now()"
        parsed_code, setup, code_type = parse_code(code2)
        shell._execute(parsed_code, setup, code_type)

        script = shell.export_history()

        # Import should appear at top before steps
        lines = script.split("\n")

        # Find where steps start and where consolidated imports are
        first_step_idx = next(i for i, l in enumerate(lines) if "# Step 1" in l)

        # The consolidated import should be before the first step
        consolidated_section = "\n".join(lines[:first_step_idx])
        assert "from datetime import datetime" in consolidated_section

        # Steps should still have the full code (imports aren't removed from steps)
        steps_section = "\n".join(lines[first_step_idx:])
        assert "from datetime import datetime" in steps_section

    def test_export_to_file(self, shell, tmp_path):
        """Export saves to file when filename provided."""
        parsed_code, setup, code_type = parse_code("2 + 2")
        shell._execute(parsed_code, setup, code_type)

        # Use temp directory
        old_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            result = shell.export_history(filename="test_export")

            # Should return confirmation
            assert "Exported" in result
            assert "test_export.py" in result

            # File should exist
            filepath = tmp_path / "test_export.py"
            assert filepath.exists()

            # File should contain code
            content = filepath.read_text()
            assert "2 + 2" in content
        finally:
            os.chdir(old_cwd)

    def test_export_rejects_absolute_paths(self, shell):
        """Export rejects absolute paths for security."""
        parsed_code, setup, code_type = parse_code("2 + 2")
        shell._execute(parsed_code, setup, code_type)

        with pytest.raises(ValueError, match="Absolute paths not allowed"):
            shell.export_history(filename="/tmp/evil.py")

    def test_export_adds_py_extension(self, shell, tmp_path):
        """Export adds .py extension if not present."""
        parsed_code, setup, code_type = parse_code("2 + 2")
        shell._execute(parsed_code, setup, code_type)

        old_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            shell.export_history(filename="test_export")

            # Should create test_export.py
            filepath = tmp_path / "test_export.py"
            assert filepath.exists()
        finally:
            os.chdir(old_cwd)

    def test_export_excludes_stdout(self, shell):
        """Export does not include stdout output."""
        parsed_code, setup, code_type = parse_code('print("Hello, World!")')
        shell._execute(parsed_code, setup, code_type)

        script = shell.export_history()

        assert "# Hello, World!" not in script
        assert 'print("Hello, World!")' in script

    def test_export_multiple_steps(self, shell):
        """Export handles multiple execution steps."""
        # Execute multiple times
        for i in range(3):
            parsed_code, setup, code_type = parse_code(f"{i} + {i}")
            shell._execute(parsed_code, setup, code_type)

        script = shell.export_history()

        # Should have all three steps
        assert "# Step 1" in script
        assert "# Step 2" in script
        assert "# Step 3" in script
        assert "0 + 0" in script
        assert "1 + 1" in script
        assert "2 + 2" in script


class TestClearHistory:
    def test_clear_history_clears_entries(self, shell):
        """Clear history removes all entries."""
        parsed_code, setup, code_type = parse_code("2 + 2")
        shell._execute(parsed_code, setup, code_type)
        shell._execute(parsed_code, setup, code_type)

        assert len(shell.history) == 2

        shell.clear_history()

        assert len(shell.history) == 0

    def test_clear_history_allows_fresh_export(self, shell):
        """Clear history allows clean export after messy exploration."""
        # Messy exploration
        parsed_code, setup, code_type = parse_code("1 / 0")
        shell._execute(parsed_code, setup, code_type)
        shell._execute(parsed_code, setup, code_type)

        # Clear
        shell.clear_history()

        # Clean solution
        parsed_code, setup, code_type = parse_code("2 + 2")
        shell._execute(parsed_code, setup, code_type)

        # Export should only have clean solution
        script = shell.export_history(include_errors=True)
        assert "1 / 0" not in script
        assert "2 + 2" in script
