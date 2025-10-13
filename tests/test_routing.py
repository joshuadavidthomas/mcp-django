from __future__ import annotations

import inspect
from pathlib import Path

import pytest

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
from mcp_django.routing import get_view_name
from tests.urls import ArticleCreate as DummyCreateView
from tests.urls import ArticleDelete as DummyDeleteView
from tests.urls import ArticleDetail as DummyDetailView
from tests.urls import BasicView as DummyView
from tests.urls import cached_get_view as stacked_decorators_view
from tests.urls import dummy_view as plain_function_view
from tests.urls import get_only_view as require_get_decorated_view
from tests.urls import multi_method_view as require_http_methods_decorated_view


@pytest.fixture
def sample_routes():
    return [
        RouteSchema(
            pattern="home/",
            name="home_page",
            namespace=None,
            parameters=[],
            view=FunctionViewSchema(
                name="test.view1",
                type=ViewType.FUNCTION,
                source_path=Path("test.py"),
                methods=[],
            ),
        ),
        RouteSchema(
            pattern="about/",
            name="about_page",
            namespace=None,
            parameters=[],
            view=FunctionViewSchema(
                name="test.view2",
                type=ViewType.FUNCTION,
                source_path=Path("test.py"),
                methods=[],
            ),
        ),
        RouteSchema(
            pattern="home/detail/",
            name=None,
            namespace=None,
            parameters=[],
            view=FunctionViewSchema(
                name="test.view3",
                type=ViewType.FUNCTION,
                source_path=Path("test.py"),
                methods=[],
            ),
        ),
        RouteSchema(
            pattern="get-only/",
            name=None,
            namespace=None,
            parameters=[],
            view=FunctionViewSchema(
                name="test.view4",
                type=ViewType.FUNCTION,
                source_path=Path("test.py"),
                methods=[ViewMethod.GET],
            ),
        ),
        RouteSchema(
            pattern="post-only/",
            name=None,
            namespace=None,
            parameters=[],
            view=FunctionViewSchema(
                name="test.view5",
                type=ViewType.FUNCTION,
                source_path=Path("test.py"),
                methods=[ViewMethod.POST],
            ),
        ),
        RouteSchema(
            pattern="unspecified/",
            name=None,
            namespace=None,
            parameters=[],
            view=FunctionViewSchema(
                name="test.view6",
                type=ViewType.FUNCTION,
                source_path=Path("test.py"),
                methods=[],
            ),
        ),
        RouteSchema(
            pattern="api/users/",
            name="api_users",
            namespace=None,
            parameters=[],
            view=FunctionViewSchema(
                name="test.view7",
                type=ViewType.FUNCTION,
                source_path=Path("test.py"),
                methods=[ViewMethod.GET],
            ),
        ),
        RouteSchema(
            pattern="api/posts/",
            name="api_posts",
            namespace=None,
            parameters=[],
            view=FunctionViewSchema(
                name="test.view8",
                type=ViewType.FUNCTION,
                source_path=Path("test.py"),
                methods=[ViewMethod.GET],
            ),
        ),
        RouteSchema(
            pattern="web/users/",
            name="web_users",
            namespace=None,
            parameters=[],
            view=FunctionViewSchema(
                name="test.view9",
                type=ViewType.FUNCTION,
                source_path=Path("test.py"),
                methods=[ViewMethod.GET],
            ),
        ),
    ]


def test_function_view_schema_plain_function():
    schema = FunctionViewSchema.from_callback(plain_function_view)

    assert isinstance(schema, FunctionViewSchema)
    assert schema.type == ViewType.FUNCTION
    assert schema.name.endswith("dummy_view")
    assert schema.methods == []
    assert isinstance(schema.source_path, Path)


@pytest.mark.parametrize(
    "view,expected_methods",
    [
        (require_get_decorated_view, [ViewMethod.GET]),
        (
            require_http_methods_decorated_view,
            [ViewMethod.GET, ViewMethod.POST, ViewMethod.PUT],
        ),
        (stacked_decorators_view, []),
    ],
)
def test_function_view_schema_decorator_detection(view, expected_methods):
    schema = FunctionViewSchema.from_callback(view)
    assert isinstance(schema, FunctionViewSchema)
    assert schema.type == ViewType.FUNCTION
    assert set(schema.methods) == set(expected_methods)


def test_class_view_schema_basic_view():
    schema = ClassViewSchema.from_callback(DummyView)

    assert isinstance(schema, ClassViewSchema)
    assert schema.type == ViewType.CLASS
    assert schema.name.endswith("BasicView")
    assert schema.class_bases == ["View"]
    assert ViewMethod.GET in schema.methods
    assert ViewMethod.POST in schema.methods
    assert isinstance(schema.source_path, Path)


@pytest.mark.parametrize(
    "view_class,base_name,expected_in,expected_not_in",
    [
        (
            DummyDetailView,
            "DetailView",
            [ViewMethod.GET],
            [ViewMethod.POST, ViewMethod.PUT, ViewMethod.DELETE],
        ),
        (DummyCreateView, "CreateView", [ViewMethod.GET, ViewMethod.POST], []),
        (
            DummyDeleteView,
            "DeleteView",
            [ViewMethod.GET, ViewMethod.POST, ViewMethod.DELETE],
            [],
        ),
    ],
)
def test_class_view_schema_generic_views(
    view_class, base_name, expected_in, expected_not_in
):
    schema = ClassViewSchema.from_callback(view_class)
    assert isinstance(schema, ClassViewSchema)
    assert schema.type == ViewType.CLASS
    assert base_name in schema.class_bases
    for method in expected_in:
        assert method in schema.methods
    for method in expected_not_in:
        assert method not in schema.methods


def test_class_view_schema_as_view_callback():
    callback = DummyView.as_view()
    schema = ClassViewSchema.from_callback(callback)

    assert isinstance(schema, ClassViewSchema)
    assert "BasicView" in schema.name
    assert schema.class_bases == ["View"]


def test_get_view_func_unwraps_decorators():
    view_func = get_view_func(stacked_decorators_view)

    assert view_func.__name__ == "cached_get_view"
    assert not hasattr(view_func, "__wrapped__")


def test_get_view_func_extracts_view_class_from_as_view():
    callback = DummyView.as_view()
    view_func = get_view_func(callback)

    assert inspect.isclass(view_func)
    assert view_func == DummyView


@pytest.mark.parametrize(
    "obj,expected_suffix",
    [
        (plain_function_view, "dummy_view"),
        (DummyView, "BasicView"),
    ],
    ids=["function", "class"],
)
def test_get_view_name(obj, expected_suffix):
    name = get_view_name(obj)
    assert "." in name
    assert name.endswith(expected_suffix)


@pytest.mark.parametrize(
    "obj,expected_marker",
    [
        (plain_function_view, "urls.py"),
        (DummyView, "urls.py"),
        (int, "unknown"),
    ],
    ids=["function", "class", "builtin"],
)
def test_get_source_file_path(obj, expected_marker):
    result = get_source_file_path(obj)
    assert isinstance(result, Path)

    if expected_marker == "unknown":
        assert result == Path("unknown")
    else:
        assert expected_marker in str(result)


@pytest.mark.parametrize(
    "pattern,expected",
    [
        ("home/", []),
        ("about/contact/", []),
        ("", []),
        ("no-params/", []),
        ("blog/<int:pk>/", ["pk"]),
        ("user/<str:username>/", ["username"]),
        ("blog/<int:year>/<int:month>/<slug:slug>/", ["year", "month", "slug"]),
        (
            "api/v1/users/<uuid:user_id>/posts/<int:post_id>/",
            ["user_id", "post_id"],
        ),
        ("items/<pk>/", ["pk"]),
        ("users/<username>/profile/", ["username"]),
        ("broken/<int:>/", []),
        ("weird/<:name>/", []),
        ("<int:a>/<int:b>/", ["a", "b"]),
    ],
)
def test_extract_url_parameters(pattern, expected):
    assert extract_url_parameters(pattern) == expected


def test_filter_routes_by_pattern(sample_routes):
    filtered = filter_routes(sample_routes, pattern="home")

    assert len(filtered) == 2
    assert all("home" in route.pattern for route in filtered)


def test_filter_routes_by_name(sample_routes):
    filtered = filter_routes(sample_routes, name="home")

    assert len(filtered) == 1
    assert filtered[0].name == "home_page"
    assert all(route.name is not None for route in filtered)


def test_filter_routes_by_method(sample_routes):
    filtered = filter_routes(sample_routes, method=ViewMethod.GET)

    assert len(filtered) >= 2
    for route in filtered:
        if route.view.methods:
            assert ViewMethod.GET in route.view.methods


def test_filter_routes_combines_criteria_with_and(sample_routes):
    filtered = filter_routes(
        sample_routes, pattern="api", name="users", method=ViewMethod.GET
    )

    assert len(filtered) == 1
    assert filtered[0].pattern == "api/users/"
    assert filtered[0].name == "api_users"


def test_filter_routes_empty_list():
    filtered = filter_routes([])
    assert filtered == []


def test_filter_routes_no_matches(sample_routes):
    filtered = filter_routes(sample_routes, pattern="NONEXISTENT")
    assert filtered == []


def test_route_count_matches_urlconf_integration():
    routes = get_all_routes()

    expected_routes = [
        "home",
        "get_only",
        "multi_method",
        "cached_get",
        "basic_view",
        "article_detail",
        "article_create",
        "article_delete",
        "item_by_slug",
        "archive_detail",
        "blog:post-list",
        "v1:users:user-detail",
        "v1:users:user-posts",
    ]

    route_names = []
    for route in routes:
        if route.namespace and route.name:
            route_names.append(f"{route.namespace}:{route.name}")
        elif route.name:
            route_names.append(route.name)

    for expected in expected_routes:
        assert expected in route_names, f"Expected route '{expected}' not found"
