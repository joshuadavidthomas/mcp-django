from __future__ import annotations

import os
from pathlib import Path

import pytest

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
        shell._execute("x = 2 + 2")

        script = shell.export_history()

        assert "# Django Shell Session Export" in script
        assert "# Step 1" in script
        assert "x = 2 + 2" in script

    def test_export_excludes_output(self, shell):
        """Export does not include execution results."""
        shell._execute("print(2 + 2)")

        script = shell.export_history()

        assert "# → 4" not in script
        assert "print(2 + 2)" in script

    def test_export_excludes_errors(self, shell):
        """Export excludes error results."""
        shell._execute("1 / 0")

        script = shell.export_history()

        # Should have header but no steps
        assert "# Django Shell Session Export" in script
        assert "1 / 0" not in script

    def test_export_continuous_step_numbers(self, shell):
        """Export has continuous step numbers even when errors are skipped."""
        # Execute: success, error, success
        shell._execute("x = 2 + 2")

        shell._execute("1 / 0")

        shell._execute("y = 3 + 3")

        script = shell.export_history()

        # Should have Step 1 and Step 2 (not Step 1 and Step 3)
        assert "# Step 1" in script
        assert "# Step 2" in script
        assert "# Step 3" not in script
        assert "x = 2 + 2" in script
        assert "1 / 0" not in script
        assert "y = 3 + 3" in script

    def test_export_deduplicates_imports(self, shell):
        """Export always consolidates imports at the top."""
        # Execute code with same import twice (without DB access)
        code1 = "from datetime import datetime\nx = datetime.now()"
        shell._execute(code1)

        code2 = "from datetime import datetime\ny = datetime.now()"
        shell._execute(code2)

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
        shell._execute("x = 2 + 2")

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
            assert "x = 2 + 2" in content
        finally:
            os.chdir(old_cwd)

    def test_export_rejects_absolute_paths(self, shell):
        """Export rejects absolute paths for security."""
        shell._execute("x = 2 + 2")

        with pytest.raises(ValueError, match="Absolute paths not allowed"):
            shell.export_history(filename="/tmp/evil.py")

    def test_export_adds_py_extension(self, shell, tmp_path):
        """Export adds .py extension if not present."""
        shell._execute("x = 2 + 2")

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
        shell._execute('print("Hello, World!")')

        script = shell.export_history()

        assert "# Hello, World!" not in script
        assert 'print("Hello, World!")' in script

    def test_export_multiple_steps(self, shell):
        """Export handles multiple execution steps."""
        # Execute multiple times
        for i in range(3):
            shell._execute(f"x{i} = {i} + {i}")

        script = shell.export_history()

        # Should have all three steps
        assert "# Step 1" in script
        assert "# Step 2" in script
        assert "# Step 3" in script
        assert "x0 = 0 + 0" in script
        assert "x1 = 1 + 1" in script
        assert "x2 = 2 + 2" in script

    def test_export_to_file_with_long_output(self, shell, tmp_path):
        """Export truncates preview for files with more than 20 lines."""
        shell._execute("x = 2 + 2")

        # Execute enough times to create > 20 lines (header + steps)
        for i in range(10):
            shell._execute(f"x{i} = {i}")

        old_cwd = Path.cwd()
        os.chdir(tmp_path)

        try:
            result = shell.export_history(filename="test_long")

            # Should mention truncation
            assert "more lines" in result
        finally:
            os.chdir(old_cwd)

    def test_export_with_invalid_syntax_in_history(self, shell):
        """Export handles code with syntax errors gracefully."""
        from mcp_django.shell.core import StatementResult

        # Manually add a result with code that can't be parsed
        # (This simulates a defensive case that shouldn't normally happen)
        invalid_result = StatementResult(
            code="if x == 1:",  # Missing body, invalid syntax
            stdout="",
            stderr="",
        )
        shell.history.append(invalid_result)

        # Should not crash, just include the code as-is
        script = shell.export_history()

        assert "if x == 1:" in script


class TestClearHistory:
    def test_clear_history_clears_entries(self, shell):
        """Clear history removes all entries."""
        shell._execute("x = 2 + 2")
        shell._execute("x = 2 + 2")

        assert len(shell.history) == 2

        shell.clear_history()

        assert len(shell.history) == 0

    def test_clear_history_allows_fresh_export(self, shell):
        """Clear history allows clean export after messy exploration."""
        # Messy exploration
        shell._execute("1 / 0")
        shell._execute("1 / 0")

        # Clear
        shell.clear_history()

        # Clean solution
        shell._execute("x = 2 + 2")

        # Export should only have clean solution
        script = shell.export_history()
        assert "1 / 0" not in script
        assert "x = 2 + 2" in script
