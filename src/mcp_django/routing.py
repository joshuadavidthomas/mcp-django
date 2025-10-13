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


def introspect_view(callback: Any) -> ViewSchema:
    """Introspect a Django view callback to extract metadata."""
    view_func = callback
    while hasattr(view_func, "__wrapped__"):
        view_func = view_func.__wrapped__

    is_class = inspect.isclass(view_func)

    module = inspect.getmodule(view_func)
    if module:
        name = f"{module.__name__}.{view_func.__name__}"
    else:
        name = view_func.__name__

    source_path = get_source_file_path(view_func)

    if is_class:
        bases = [
            base.__name__ for base in view_func.__bases__ if base.__name__ != "object"
        ]
        class_bases = bases if bases else None

        if hasattr(view_func, "http_method_names"):
            methods = [m.upper() for m in view_func.http_method_names]
        else:
            methods = [
                "GET",
                "HEAD",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
                "OPTIONS",
                "TRACE",
            ]
    else:
        class_bases = None
        methods = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"]

    return ViewSchema(
        name=name,
        type="class" if is_class else "function",
        source_path=source_path,
        class_bases=class_bases,
        methods=methods,
    )
