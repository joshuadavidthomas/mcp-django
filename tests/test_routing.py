from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from django.contrib.auth.decorators import login_required
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
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
from mcp_django.routing import get_view_name


def plain_function_view(request):
    return None


@require_GET
def require_get_decorated_view(request):
    return None


@require_POST
def require_post_decorated_view(request):
    return None


@require_http_methods(["GET", "POST", "PUT"])
def require_http_methods_decorated_view(request):
    return None


@login_required
@require_POST
def stacked_decorators_view(request):
    return None


@cache_page(60)
@require_GET
def cache_and_require_get_view(request):
    return None


class DummyView(View):
    def get(self, request):
        return None

    def post(self, request):
        return None


class DummyDetailView(DetailView):
    model = None


class DummyCreateView(CreateView):
    model = None


class DummyDeleteView(DeleteView):
    model = None


class DummyListView(ListView):
    model = None


def test_function_view_schema_plain_function():
    schema = FunctionViewSchema.from_callback(plain_function_view)

    assert isinstance(schema, FunctionViewSchema)
    assert schema.type == ViewType.FUNCTION
    assert schema.name.endswith("plain_function_view")
    assert schema.methods == []
    assert isinstance(schema.source_path, Path)


@pytest.mark.parametrize(
    "view,expected_methods",
    [
        (require_get_decorated_view, [ViewMethod.GET]),
        (require_post_decorated_view, [ViewMethod.POST]),
        (
            require_http_methods_decorated_view,
            [ViewMethod.GET, ViewMethod.POST, ViewMethod.PUT],
        ),
        (stacked_decorators_view, []),
        (cache_and_require_get_view, []),
    ],
    ids=[
        "require_get",
        "require_post",
        "require_http_methods",
        "stacked_login_post",
        "cache_and_get",
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
    assert schema.name.endswith("DummyView")
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
        (DummyListView, "ListView", [ViewMethod.GET], [ViewMethod.POST]),
    ],
    ids=["DetailView", "CreateView", "DeleteView", "ListView"],
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
    assert "DummyView" in schema.name
    assert schema.class_bases == ["View"]


def test_get_view_func_unwraps_decorators():
    view_func = get_view_func(stacked_decorators_view)

    assert view_func.__name__ == "stacked_decorators_view"
    assert not hasattr(view_func, "__wrapped__")


def test_get_view_func_extracts_view_class_from_as_view():
    callback = DummyView.as_view()
    view_func = get_view_func(callback)

    assert inspect.isclass(view_func)
    assert view_func == DummyView


def test_get_view_name_with_module():
    name = get_view_name(plain_function_view)

    assert "." in name
    assert name.endswith("plain_function_view")


def test_get_view_name_class():
    name = get_view_name(DummyView)

    assert "." in name
    assert name.endswith("DummyView")


@pytest.mark.parametrize(
    "obj,expected_marker",
    [
        (plain_function_view, "test_routing.py"),
        (DummyView, "test_routing.py"),
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
    ids=[
        "empty_home",
        "empty_nested",
        "empty_string",
        "no_params",
        "single_int",
        "single_str",
        "multiple_mixed",
        "multiple_uuid_int",
        "no_converter_pk",
        "no_converter_username",
        "malformed_empty_name",
        "malformed_empty_converter",
        "adjacent_params",
    ],
)
def test_extract_url_parameters(pattern, expected):
    assert extract_url_parameters(pattern) == expected


def test_filter_routes_by_pattern():
    routes = [
        RouteSchema(
            pattern="home/",
            name=None,
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
            name=None,
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
    ]

    filtered = filter_routes(routes, pattern="home")

    assert len(filtered) == 2
    assert all("home" in route.pattern for route in filtered)


def test_filter_routes_by_name():
    routes = [
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
            pattern="unnamed/",
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
    ]

    filtered = filter_routes(routes, name="home")

    assert len(filtered) == 1
    assert filtered[0].name == "home_page"
    assert all(route.name is not None for route in filtered)


def test_filter_routes_by_method():
    routes = [
        RouteSchema(
            pattern="get-only/",
            name=None,
            namespace=None,
            parameters=[],
            view=FunctionViewSchema(
                name="test.view1",
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
                name="test.view2",
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
                name="test.view3",
                type=ViewType.FUNCTION,
                source_path=Path("test.py"),
                methods=[],
            ),
        ),
    ]

    filtered = filter_routes(routes, method=ViewMethod.GET)

    assert len(filtered) == 2
    for route in filtered:
        if route.view.methods:
            assert ViewMethod.GET in route.view.methods


def test_filter_routes_combines_criteria_with_and():
    routes = [
        RouteSchema(
            pattern="api/users/",
            name="api_users",
            namespace=None,
            parameters=[],
            view=FunctionViewSchema(
                name="test.view1",
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
                name="test.view2",
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
                name="test.view3",
                type=ViewType.FUNCTION,
                source_path=Path("test.py"),
                methods=[ViewMethod.GET],
            ),
        ),
    ]

    filtered = filter_routes(routes, pattern="api", name="users", method=ViewMethod.GET)

    assert len(filtered) == 1
    assert filtered[0].pattern == "api/users/"
    assert filtered[0].name == "api_users"


def test_filter_routes_empty_list():
    filtered = filter_routes([])

    assert filtered == []


def test_filter_routes_no_matches():
    routes = [
        RouteSchema(
            pattern="home/",
            name="home",
            namespace=None,
            parameters=[],
            view=FunctionViewSchema(
                name="test.view1",
                type=ViewType.FUNCTION,
                source_path=Path("test.py"),
                methods=[],
            ),
        ),
    ]

    filtered = filter_routes(routes, pattern="NONEXISTENT")

    assert filtered == []


def test_full_extraction_pipeline_integration():
    routes = get_all_routes()

    assert isinstance(routes, list)
    assert len(routes) > 0
    assert all(isinstance(route, RouteSchema) for route in routes)

    for route in routes:
        assert isinstance(route.pattern, str)
        assert route.name is None or isinstance(route.name, str)
        assert route.namespace is None or isinstance(route.namespace, str)
        assert isinstance(route.parameters, list)
        assert isinstance(route.view, FunctionViewSchema | ClassViewSchema)


def test_filtering_workflow_integration():
    routes = get_all_routes()

    get_routes = filter_routes(routes, method=ViewMethod.GET)
    assert len(get_routes) > 0

    named_routes = [r for r in routes if r.name]
    if named_routes:
        test_name = named_routes[0].name
        name_filtered = filter_routes(routes, name=test_name)
        assert len(name_filtered) > 0
        assert all(test_name in (route.name or "") for route in name_filtered)


def test_decorator_detection_from_urlconf_integration():
    routes = get_all_routes()

    get_only_routes = [
        r for r in routes if r.name == "get_only" or r.name == "cached_get"
    ]
    assert len(get_only_routes) > 0

    for route in get_only_routes:
        if route.view.methods:
            assert ViewMethod.GET in route.view.methods


def test_namespace_composition_integration():
    routes = get_all_routes()

    blog_routes = [r for r in routes if r.namespace == "blog"]
    assert len(blog_routes) > 0

    post_list = next((r for r in blog_routes if r.name == "post-list"), None)
    assert post_list is not None
    assert post_list.namespace == "blog"

    nested_routes = [r for r in routes if r.namespace == "v1:users"]
    assert len(nested_routes) > 0

    user_detail = next((r for r in nested_routes if r.name == "user-detail"), None)
    assert user_detail is not None
    assert user_detail.namespace == "v1:users"


def test_parameter_extraction_from_urlconf_integration():
    routes = get_all_routes()

    article_detail = next(
        (r for r in routes if r.name == "article_detail"),
        None,
    )
    assert article_detail is not None
    assert "pk" in article_detail.parameters

    item_by_slug = next(
        (r for r in routes if r.name == "item_by_slug"),
        None,
    )
    assert item_by_slug is not None
    assert "slug" in item_by_slug.parameters

    archive_detail = next(
        (r for r in routes if r.name == "archive_detail"),
        None,
    )
    assert archive_detail is not None
    assert "year" in archive_detail.parameters
    assert "month" in archive_detail.parameters
    assert "slug" in archive_detail.parameters


def test_route_count_matches_urlconf_integration():
    routes = get_all_routes()

    expected_routes = [
        "home",
        "get_only",
        "post_only",
        "multi_method",
        "protected_post",
        "cached_get",
        "basic_view",
        "article_list",
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


def test_performance_benchmark_integration():
    import time

    start = time.time()
    routes = get_all_routes()
    elapsed = time.time() - start

    assert elapsed < 1.0, f"Route extraction took {elapsed:.3f}s (expected < 1.0s)"
    assert len(routes) > 0
