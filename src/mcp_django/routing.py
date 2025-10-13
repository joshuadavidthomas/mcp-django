from __future__ import annotations

import inspect
import re
from collections.abc import Iterable
from enum import Enum
from pathlib import Path
from typing import Any
from typing import Literal

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


class FunctionViewSchema(BaseModel):
    """Schema for function-based view.

    Fields:
        name: Fully qualified view name (module.function)
        type: Always ViewType.FUNCTION
        source_path: Path to source file, or Path("unknown")
        methods: List of allowed HTTP methods. Empty list indicates methods
                 could not be determined. Django's built-in method decorators
                 (@require_GET, @require_POST, @require_http_methods) are
                 automatically detected via closure inspection.
    """

    name: str
    type: Literal[ViewType.FUNCTION]
    source_path: Path
    methods: list[ViewMethod]


class ClassViewSchema(BaseModel):
    """Schema for class-based view.

    Fields:
        name: Fully qualified view name (module.ClassName)
        type: Always ViewType.CLASS
        source_path: Path to source file, or Path("unknown")
        methods: List of HTTP methods actually implemented by the view.
                 Determined by checking which method handlers (get, post, etc.)
                 are defined on the class.
        class_bases: List of base class names, excluding 'object'.
                     Example: ['ListView', 'LoginRequiredMixin']
    """

    name: str
    type: Literal[ViewType.CLASS]
    source_path: Path
    methods: list[ViewMethod]
    class_bases: list[str]


ViewSchema = FunctionViewSchema | ClassViewSchema


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

    Supports Django's standard path converters (int, str, slug, uuid, path)
    and any custom converter names using word characters (a-z, A-Z, 0-9, _).

    Args:
        pattern: Django URL pattern string

    Returns:
        List of parameter names extracted from the pattern

    Examples:
        >>> extract_url_parameters("blog/<int:pk>/")
        ["pk"]
        >>> extract_url_parameters("blog/<pk>/")
        ["pk"]
        >>> extract_url_parameters("api/<uuid:id>/posts/<int:post_id>/")
        ["id", "post_id"]
    """
    param_regex = r"<(?:\w+:)?(\w+)>"
    return re.findall(param_regex, pattern)


def _extract_methods_from_closure(view_func: Any) -> list[ViewMethod] | None:
    """Extract allowed HTTP methods from Django decorator closure.

    Django's method decorators (@require_GET, @require_http_methods, etc.)
    store the allowed methods in the function's closure. This extracts them.

    Returns:
        List of allowed ViewMethod enums if decorator found, None otherwise.
    """
    if not hasattr(view_func, "__closure__") or not view_func.__closure__:
        return None

    for cell in view_func.__closure__:
        try:
            content = cell.cell_contents
            if isinstance(content, list) and content:
                if all(isinstance(m, str) for m in content):
                    methods = []
                    for method_str in content:
                        if method_str in ViewMethod.__members__:
                            methods.append(ViewMethod[method_str])
                    if methods:
                        return methods
        except (AttributeError, ValueError):
            continue

    return None


def introspect_view(callback: Any) -> FunctionViewSchema | ClassViewSchema:
    """Introspect a Django view callback to extract metadata.

    Handles both function-based views (FBVs) and class-based views (CBVs),
    including .as_view() callbacks. For FBVs, attempts to detect HTTP method
    restrictions via closure inspection of Django decorators.

    Args:
        callback: View function, class, or .as_view() callback

    Returns:
        FunctionViewSchema for FBVs with method detection via decorators,
        ClassViewSchema for CBVs with methods determined by checking which
        method handlers (get, post, etc.) are actually implemented.
    """
    original_callback = callback
    view_func = callback

    if hasattr(view_func, "view_class"):
        view_func = view_func.view_class

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
        class_bases = bases if bases else []

        method_names = getattr(
            view_func,
            "http_method_names",
            ["get", "post", "put", "patch", "delete", "head", "options", "trace"],
        )

        implemented_methods = []
        for method_name in method_names:
            if hasattr(view_func, method_name):
                implemented_methods.append(ViewMethod[method_name.upper()])

        methods = implemented_methods if implemented_methods else []

        return ClassViewSchema(
            name=name,
            type=ViewType.CLASS,
            source_path=source_path,
            class_bases=class_bases,
            methods=methods,
        )
    else:
        detected_methods = _extract_methods_from_closure(original_callback)

        if detected_methods is None:
            detected_methods = []

        return FunctionViewSchema(
            name=name,
            type=ViewType.FUNCTION,
            source_path=source_path,
            methods=detected_methods,
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
    """Get all Django URL routes by recursively walking URLconf.

    Traverses the entire URL resolver tree starting from ROOT_URLCONF,
    extracting route patterns, view metadata, namespaces, and parameters.

    Returns:
        List of RouteSchema objects, one per URL pattern

    Note:
        For projects with many routes (1000+), this may take a few seconds
        on first call. Results are not cached.
    """
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

    Args:
        method: HTTP method name (case-insensitive). Valid values: GET, POST, PUT,
                PATCH, DELETE, HEAD, OPTIONS, TRACE
        name: Route name substring for filtering (case-sensitive)
        pattern: URL pattern substring for filtering (case-sensitive)

    Returns:
        Filtered list of routes matching all provided criteria

    Raises:
        ValueError: If method is not a valid HTTP method name
        TypeError: If name or pattern is not a string
    """
    filtered = routes

    if method:
        try:
            method_enum = ViewMethod[method.upper()]
            filtered = [
                r
                for r in filtered
                if not r.view.methods or method_enum in r.view.methods
            ]
        except KeyError as exc:
            valid_methods = ", ".join(m.name for m in ViewMethod)
            raise ValueError(
                f"Invalid HTTP method: {method!r}. Valid methods: {valid_methods}"
            ) from exc

    if name is not None:
        if not isinstance(name, str):
            raise TypeError(f"name must be str, not {type(name).__name__}")
        filtered = [r for r in filtered if r.name and name in r.name]

    if pattern is not None:
        if not isinstance(pattern, str):
            raise TypeError(f"pattern must be str, not {type(pattern).__name__}")
        filtered = [r for r in filtered if pattern in r.pattern]

    return filtered
