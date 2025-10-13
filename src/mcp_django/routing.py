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

    @classmethod
    def from_callback(cls, callback: Any):
        view_func = get_view_func(callback)
        name = get_view_name(view_func)
        source_path = get_source_file_path(view_func)
        methods = _extract_methods_from_closure(callback)

        if methods is None:
            methods = []

        return FunctionViewSchema(
            name=name,
            type=ViewType.FUNCTION,
            source_path=source_path,
            methods=methods,
        )


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

    @classmethod
    def from_callback(cls, callback: Any):
        view_func = get_view_func(callback)
        name = get_view_name(view_func)
        source_path = get_source_file_path(view_func)

        bases = [
            base.__name__ for base in view_func.__bases__ if base.__name__ != "object"
        ]
        class_bases = bases if bases else []

        implemented_methods = [
            method for method in ViewMethod if hasattr(view_func, method.value.lower())
        ]

        methods = implemented_methods if implemented_methods else []

        return cls(
            name=name,
            type=ViewType.CLASS,
            source_path=source_path,
            class_bases=class_bases,
            methods=methods,
        )


ViewSchema = FunctionViewSchema | ClassViewSchema


class RouteSchema(BaseModel):
    """Schema for a complete Django URL route.

    Fields:
        pattern: Full URL pattern string (e.g., "blog/<int:pk>/")
        name: Route name for reverse URL lookup, or None if unnamed
        namespace: URL namespace (e.g., "admin"), or None if not namespaced
        parameters: List of URL parameter names extracted from pattern
        view: View handler (FunctionViewSchema or ClassViewSchema)
    """

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
        ['pk']
        >>> extract_url_parameters("blog/<pk>/")
        ['pk']
        >>> extract_url_parameters("api/<uuid:id>/posts/<int:post_id>/")
        ['id', 'post_id']
    """
    # Matches <converter:name> or <name> and captures the parameter name
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


def get_view_func(callback: Any):
    """Extract the actual view function or class from a callback.

    Unwraps decorators and extracts view_class from .as_view() callbacks.

    Returns:
        The underlying function or class object
    """
    view_func = callback

    if hasattr(view_func, "view_class"):
        view_func = view_func.view_class

    while hasattr(view_func, "__wrapped__"):
        view_func = view_func.__wrapped__

    return view_func


def get_view_name(view_func: Any):
    """Get the fully qualified name of a view function or class.

    Returns:
        Fully qualified name (module.name) if module is found, otherwise just the name
    """
    module = inspect.getmodule(view_func)
    if module:
        name = f"{module.__name__}.{view_func.__name__}"
    else:
        name = view_func.__name__
    return name


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

            view_func = get_view_func(pattern.callback)
            if inspect.isclass(view_func):
                view_schema = ClassViewSchema.from_callback(pattern.callback)
            else:
                view_schema = FunctionViewSchema.from_callback(pattern.callback)

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
    method: ViewMethod | None = None,
    name: str | None = None,
    pattern: str | None = None,
) -> list[RouteSchema]:
    """Filter routes using contains matching on each parameter.

    All filters are AND'd together - routes must match all provided filters.

    Args:
        method: ViewMethod enum or None for filtering by HTTP method
        name: Route name substring for filtering (case-sensitive)
        pattern: URL pattern substring for filtering (case-sensitive)

    Returns:
        Filtered list of routes matching all provided criteria

    Raises:
        ValueError: If method is not a valid HTTP method name
    """
    filtered = routes

    if method:
        try:
            filtered = [
                r for r in filtered if not r.view.methods or method in r.view.methods
            ]
        except KeyError as exc:
            valid_methods = ", ".join(m.name for m in ViewMethod)
            raise ValueError(
                f"Invalid HTTP method: {method!r}. Valid methods: {valid_methods}"
            ) from exc

    if name is not None:
        filtered = [r for r in filtered if r.name and name in r.name]

    if pattern is not None:
        filtered = [r for r in filtered if pattern in r.pattern]

    return filtered
