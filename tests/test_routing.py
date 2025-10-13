from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from django.views import View
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView

from mcp_django.routing import ClassViewSchema
from mcp_django.routing import FunctionViewSchema
from mcp_django.routing import RouteSchema
from mcp_django.routing import ViewMethod
from mcp_django.routing import ViewType
from mcp_django.routing import extract_url_parameters
from mcp_django.routing import filter_routes
from mcp_django.routing import get_all_routes
from mcp_django.routing import get_source_file_path
from mcp_django.routing import get_view_func


def test_view_schema_function():
    schema = FunctionViewSchema(
        name="myapp.views.home",
        type=ViewType.FUNCTION,
        source_path=Path("/path/to/views.py"),
        methods=[ViewMethod.GET, ViewMethod.POST],
    )

    assert schema.name == "myapp.views.home"
    assert schema.type == ViewType.FUNCTION
    assert schema.source_path == Path("/path/to/views.py")
    assert schema.methods == [ViewMethod.GET, ViewMethod.POST]


def test_view_schema_class():
    schema = ClassViewSchema(
        name="myapp.views.HomeView",
        type=ViewType.CLASS,
        source_path=Path("/path/to/views.py"),
        class_bases=["ListView", "LoginRequiredMixin"],
        methods=[ViewMethod.GET],
    )

    assert schema.name == "myapp.views.HomeView"
    assert schema.type == ViewType.CLASS
    assert schema.class_bases == ["ListView", "LoginRequiredMixin"]


def test_route_schema_basic():
    view = FunctionViewSchema(
        name="myapp.views.home",
        type=ViewType.FUNCTION,
        source_path=Path("/path/to/views.py"),
        methods=[ViewMethod.GET],
    )

    route = RouteSchema(
        pattern="home/",
        name="home",
        namespace=None,
        parameters=[],
        view=view,
    )

    assert route.pattern == "home/"
    assert route.name == "home"
    assert route.namespace is None
    assert route.parameters == []
    assert route.view == view


def test_route_schema_with_params():
    view = FunctionViewSchema(
        name="myapp.views.detail",
        type=ViewType.FUNCTION,
        source_path=Path("/path/to/views.py"),
        methods=[ViewMethod.GET],
    )

    route = RouteSchema(
        pattern="blog/<int:pk>/",
        name="blog-detail",
        namespace="blog",
        parameters=["pk"],
        view=view,
    )

    assert route.pattern == "blog/<int:pk>/"
    assert route.name == "blog-detail"
    assert route.namespace == "blog"
    assert route.parameters == ["pk"]


def test_get_source_file_path_with_function():
    def dummy_view():
        pass

    result = get_source_file_path(dummy_view)
    assert isinstance(result, Path)
    assert result != Path("unknown")
    assert "test_routing.py" in str(result)


def test_get_source_file_path_with_class():
    class DummyView:
        pass

    result = get_source_file_path(DummyView)
    assert isinstance(result, Path)
    assert result != Path("unknown")


def test_get_source_file_path_builtin():
    result = get_source_file_path(int)
    assert result == Path("unknown")


def test_extract_url_parameters_empty():
    assert extract_url_parameters("home/") == []
    assert extract_url_parameters("about/contact/") == []


def test_extract_url_parameters_single():
    assert extract_url_parameters("blog/<int:pk>/") == ["pk"]
    assert extract_url_parameters("user/<str:username>/") == ["username"]


def test_extract_url_parameters_multiple():
    assert extract_url_parameters("blog/<int:year>/<int:month>/<slug:slug>/") == [
        "year",
        "month",
        "slug",
    ]


def test_extract_url_parameters_mixed():
    assert extract_url_parameters(
        "api/v1/users/<uuid:user_id>/posts/<int:post_id>/"
    ) == [
        "user_id",
        "post_id",
    ]


def dummy_function_view(request):
    return None


class DummyClassView(View):
    def get(self, request):
        return None


class DummyListView(ListView):
    model = None


def test_introspect_view_function():
    view_func = get_view_func(dummy_function_view)
    if inspect.isclass(view_func):
        schema = ClassViewSchema.from_callback(dummy_function_view)
    else:
        schema = FunctionViewSchema.from_callback(dummy_function_view)

    assert isinstance(schema, FunctionViewSchema)
    assert schema.type == ViewType.FUNCTION
    assert schema.name.endswith("dummy_function_view")
    assert schema.methods == []
    assert isinstance(schema.source_path, Path)


def test_introspect_view_class():
    view_func = get_view_func(DummyClassView)
    if inspect.isclass(view_func):
        schema = ClassViewSchema.from_callback(DummyClassView)
    else:
        schema = FunctionViewSchema.from_callback(DummyClassView)

    assert isinstance(schema, ClassViewSchema)
    assert schema.type == ViewType.CLASS
    assert schema.name.endswith("DummyClassView")
    assert schema.class_bases == ["View"]
    assert ViewMethod.GET in schema.methods
    assert isinstance(schema.source_path, Path)


def test_introspect_view_generic():
    view_func = get_view_func(DummyListView)
    if inspect.isclass(view_func):
        schema = ClassViewSchema.from_callback(DummyListView)
    else:
        schema = FunctionViewSchema.from_callback(DummyListView)

    assert isinstance(schema, ClassViewSchema)
    assert schema.type == ViewType.CLASS
    assert schema.class_bases == ["ListView"]
    assert ViewMethod.GET in schema.methods


def test_introspect_view_as_view_callback():
    """Test that .as_view() callbacks are correctly identified as CBVs."""
    callback = DummyClassView.as_view()
    view_func = get_view_func(callback)
    if inspect.isclass(view_func):
        schema = ClassViewSchema.from_callback(callback)
    else:
        schema = FunctionViewSchema.from_callback(callback)

    assert isinstance(schema, ClassViewSchema)
    assert schema.type == ViewType.CLASS
    assert "DummyClassView" in schema.name
    assert schema.class_bases == ["View"]


def test_get_all_routes_returns_list():
    routes = get_all_routes()

    assert isinstance(routes, list)
    assert len(routes) > 0
    assert all(isinstance(route, RouteSchema) for route in routes)


def test_get_all_routes_has_expected_fields():
    routes = get_all_routes()

    route = routes[0]
    assert isinstance(route.pattern, str)
    assert route.name is None or isinstance(route.name, str)
    assert route.namespace is None or isinstance(route.namespace, str)
    assert isinstance(route.parameters, list)
    assert isinstance(route.view, FunctionViewSchema | ClassViewSchema)


def test_filter_routes_no_filters():
    routes = get_all_routes()
    filtered = filter_routes(routes)

    assert filtered == routes


def test_filter_routes_by_pattern():
    routes = get_all_routes()

    if routes:
        test_pattern = (
            routes[0].pattern[:5] if len(routes[0].pattern) >= 5 else routes[0].pattern
        )
        filtered = filter_routes(routes, pattern=test_pattern)

        assert len(filtered) > 0
        assert all(test_pattern in route.pattern for route in filtered)


def test_filter_routes_by_name():
    routes = get_all_routes()

    named_routes = [r for r in routes if r.name]
    if named_routes:
        test_name = named_routes[0].name
        filtered = filter_routes(routes, name=test_name)

        assert len(filtered) > 0
        assert all(test_name in (route.name or "") for route in filtered)


def test_filter_routes_by_method():
    routes = get_all_routes()

    filtered = filter_routes(routes, method=ViewMethod.GET)

    assert len(filtered) > 0
    for route in filtered:
        if route.view.methods:
            assert ViewMethod.GET in route.view.methods


def test_filter_routes_multiple_filters():
    routes = get_all_routes()

    if routes:
        filtered = filter_routes(
            routes, method=ViewMethod.GET, pattern=routes[0].pattern[:3]
        )

        for route in filtered:
            if route.view.methods:
                assert ViewMethod.GET in route.view.methods
        assert all(routes[0].pattern[:3] in route.pattern for route in filtered)


def test_filter_routes_no_matches():
    routes = get_all_routes()

    filtered = filter_routes(routes, pattern="NONEXISTENT_PATTERN_XYZ123")

    assert filtered == []


def dummy_require_get_view(request):
    """Dummy view with @require_GET decorator."""
    return None


dummy_require_get_view = require_GET(dummy_require_get_view)


def test_introspect_view_with_require_get_decorator():
    """Test that @require_GET decorator is detected."""
    view_func = get_view_func(dummy_require_get_view)
    if inspect.isclass(view_func):
        schema = ClassViewSchema.from_callback(dummy_require_get_view)
    else:
        schema = FunctionViewSchema.from_callback(dummy_require_get_view)

    assert isinstance(schema, FunctionViewSchema)
    assert schema.methods == [ViewMethod.GET]


def dummy_require_http_methods_view(request):
    """Dummy view with @require_http_methods decorator."""
    return None


dummy_require_http_methods_view = require_http_methods(["GET", "POST"])(
    dummy_require_http_methods_view
)


def test_introspect_view_with_require_http_methods_decorator():
    """Test that @require_http_methods decorator arguments are parsed."""
    view_func = get_view_func(dummy_require_http_methods_view)
    if inspect.isclass(view_func):
        schema = ClassViewSchema.from_callback(dummy_require_http_methods_view)
    else:
        schema = FunctionViewSchema.from_callback(dummy_require_http_methods_view)

    assert isinstance(schema, FunctionViewSchema)
    assert set(schema.methods) == {ViewMethod.GET, ViewMethod.POST}


def test_introspect_view_function_no_decorator():
    """Test that undecorated FBV returns empty methods list."""
    view_func = get_view_func(dummy_function_view)
    if inspect.isclass(view_func):
        schema = ClassViewSchema.from_callback(dummy_function_view)
    else:
        schema = FunctionViewSchema.from_callback(dummy_function_view)

    assert isinstance(schema, FunctionViewSchema)
    assert schema.methods == []


def test_filter_routes_empty_methods_included():
    """Test that views with empty methods are included in method filtering."""
    routes = get_all_routes()

    filtered = filter_routes(routes, method=ViewMethod.GET)

    for route in filtered:
        if route.view.methods:
            assert ViewMethod.GET in route.view.methods


def test_cbv_only_reports_implemented_methods():
    """CBVs should only report methods they actually implement."""
    from django.views.generic import DetailView

    view_func = get_view_func(DetailView)
    if inspect.isclass(view_func):
        schema = ClassViewSchema.from_callback(DetailView)
    else:
        schema = FunctionViewSchema.from_callback(DetailView)

    assert isinstance(schema, ClassViewSchema)
    assert ViewMethod.GET in schema.methods
    assert ViewMethod.POST not in schema.methods
    assert ViewMethod.PUT not in schema.methods
    assert ViewMethod.DELETE not in schema.methods


def test_filter_routes_method_and_name():
    """Test filtering by method and name together."""
    routes = get_all_routes()

    filtered = filter_routes(routes, method=ViewMethod.GET, name="get_only")

    assert len(filtered) > 0
    for route in filtered:
        assert not route.view.methods or ViewMethod.GET in route.view.methods
        assert route.name and "get_only" in route.name


def test_filter_routes_all_three_filters():
    """Test filtering by method, name, and pattern together."""
    routes = get_all_routes()

    filtered = filter_routes(
        routes, method=ViewMethod.GET, name="get", pattern="get-only"
    )

    for route in filtered:
        assert not route.view.methods or ViewMethod.GET in route.view.methods
        assert route.name and "get" in route.name
        assert "get-only" in route.pattern


def test_nested_namespaces():
    """Test that nested URL namespaces are correctly composed."""
    routes = get_all_routes()

    blog_routes = [r for r in routes if r.namespace == "blog"]
    assert len(blog_routes) > 0

    post_list = next((r for r in blog_routes if r.name == "post-list"), None)
    assert post_list is not None
    assert post_list.namespace == "blog"
