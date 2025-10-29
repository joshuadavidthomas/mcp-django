from __future__ import annotations

import ast
from typing import Any
from typing import Literal


def filter_existing_imports(imports: str, globals_dict: dict[str, Any]) -> str:
    tree = ast.parse(imports)

    if not all(isinstance(stmt, ast.Import | ast.ImportFrom) for stmt in tree.body):
        raise ValueError("Input must contain only import statements")

    filtered_statements: list[tuple[ast.Import | ast.ImportFrom, list[ast.alias]]] = []

    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            needed = [
                alias
                for alias in stmt.names
                if (alias.asname or alias.name.split(".")[0]) not in globals_dict
            ]
            if needed:
                filtered_statements.append((stmt, needed))

        elif isinstance(stmt, ast.ImportFrom):
            if stmt.names[0].name == "*":
                # Star imports - always include (can't easily determine what's imported)
                filtered_statements.append((stmt, stmt.names))
            else:
                needed = [
                    alias
                    for alias in stmt.names
                    if (alias.asname or alias.name) not in globals_dict
                ]
                if needed:
                    filtered_statements.append((stmt, needed))

    filtered_lines: list[str] = []

    for stmt, names in filtered_statements:
        import_parts: list[str] = []

        if isinstance(stmt, ast.ImportFrom):
            module = stmt.module or ""
            level = "." * stmt.level if stmt.level else ""
            import_parts.append(f"from {level}{module}")

        import_parts.append("import")

        name_parts = [
            f"{alias.name} as {alias.asname}" if alias.asname else alias.name
            for alias in names
        ]
        import_parts.append(", ".join(name_parts))

        filtered_lines.append(" ".join(import_parts))

    return "\n".join(filtered_lines)


def parse_code(code: str) -> tuple[str, str, Literal["expression", "statement"]]:
    """Determine how code should be executed.

    Returns:
        A tuple (main_code, setup_code, code_type), where:
        - main_code: The code to evaluate (expression) or execute (statement)
        - setup_code: Lines to execute before evaluating expressions (empty for statements)
        - code_type: "expression" or "statement"
    """

    def can_eval(code: str) -> bool:
        try:
            compile(code, "<stdin>", "eval")
            return True
        except SyntaxError:
            return False

    if can_eval(code):
        return code, "", "expression"

    lines = code.strip().splitlines()
    last_line = lines[-1] if lines else ""

    if can_eval(last_line):
        setup_code = "\n".join(lines[:-1])
        return last_line, setup_code, "expression"

    return code, "", "statement"
