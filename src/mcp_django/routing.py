from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel


class ViewSchema(BaseModel):
    name: str
    type: Literal["function", "class"]
    source_path: Path
    class_bases: list[str] | None
    methods: list[str]


class RouteSchema(BaseModel):
    pattern: str
    name: str | None
    namespace: str | None
    parameters: list[str]
    view: ViewSchema


def get_source_file_path(obj: Any) -> Path:
    """Get the source file path for a function or class.

    Returns Path("unknown") if the source cannot be determined.
    """
    try:
        return Path(inspect.getfile(obj))
    except (TypeError, OSError):
        return Path("unknown")


def extract_url_parameters(pattern: str) -> list[str]:
    """Extract parameter names from a URL pattern.

    Example: "blog/<int:pk>/" returns ["pk"]
    """
    param_regex = r"<(?:\w+:)?(\w+)>"
    return re.findall(param_regex, pattern)
