from __future__ import annotations

import inspect
import re
from collections.abc import Iterable
from enum import Enum
from pathlib import Path
from typing import Any

from django.urls import get_resolver
from django.urls.resolvers import URLPattern
from django.urls.resolvers import URLResolver
from pydantic import BaseModel


class ViewType(Enum):
    CLASS = "class"
    FUNCTION = "function"


class ViewMethod(Enum):
    DELETE = "DELETE"
    GET = "GET"
    HEAD = "HEAD"
    PATCH = "PATCH"
    POST = "POST"
    PUT = "PUT"
    OPTIONS = "OPTIONS"
    TRACE = "TRACE"


class ViewSchema(BaseModel):
    name: str
    type: ViewType
    source_path: Path
    class_bases: list[str] | None
    methods: list[ViewMethod]


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
            methods = [ViewMethod[m.upper()] for m in view_func.http_method_names]
        else:
            methods = list(ViewMethod)
    else:
        class_bases = None
        methods = list(ViewMethod)

    return ViewSchema(
        name=name,
        type=ViewType.CLASS if is_class else ViewType.FUNCTION,
        source_path=source_path,
        class_bases=class_bases,
        methods=methods,
    )


def extract_routes(
    patterns: Iterable[URLPattern | URLResolver],
    prefix: str = "",
    namespace: str | None = None,
) -> list[RouteSchema]:
    """Recursively extract routes from URL patterns."""
    routes = []

    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            current_namespace = pattern.namespace
            full_namespace: str | None
            if namespace and current_namespace:
                full_namespace = f"{namespace}:{current_namespace}"
            elif current_namespace:
                full_namespace = current_namespace
            else:
                full_namespace = namespace

            extracted_routes = extract_routes(
                pattern.url_patterns,
                prefix + str(pattern.pattern),
                full_namespace,
            )
            routes.extend(extracted_routes)

        elif isinstance(pattern, URLPattern):
            full_pattern = prefix + str(pattern.pattern)
            parameters = extract_url_parameters(full_pattern)

            view_schema = introspect_view(pattern.callback)

            route = RouteSchema(
                pattern=full_pattern,
                name=pattern.name,
                namespace=namespace,
                parameters=parameters,
                view=view_schema,
            )
            routes.append(route)

    return routes


def get_all_routes() -> list[RouteSchema]:
    """Get all Django URL routes."""
    resolver = get_resolver()
    routes = extract_routes(resolver.url_patterns)
    return routes


def filter_routes(
    routes: list[RouteSchema],
    method: str | None = None,
    name: str | None = None,
    pattern: str | None = None,
) -> list[RouteSchema]:
    """Filter routes using contains matching on each parameter.

    All filters are AND'd together - routes must match all provided filters.
    """
    filtered = routes

    if method:
        try:
            method_enum = ViewMethod[method.upper()]
            filtered = [r for r in filtered if method_enum in r.view.methods]
        except KeyError:
            filtered = []

    if name:
        filtered = [r for r in filtered if r.name and name in r.name]

    if pattern:
        filtered = [r for r in filtered if pattern in r.pattern]

    return filtered
