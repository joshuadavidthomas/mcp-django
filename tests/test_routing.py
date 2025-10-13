from __future__ import annotations

from pathlib import Path

from django.views import View
from django.views.generic import ListView

from mcp_django.routing import RouteSchema
from mcp_django.routing import ViewSchema
from mcp_django.routing import extract_url_parameters
from mcp_django.routing import filter_routes
from mcp_django.routing import get_all_routes
from mcp_django.routing import get_source_file_path
from mcp_django.routing import introspect_view


def test_view_schema_function():
    schema = ViewSchema(
        name="myapp.views.home",
        type="function",
        source_path=Path("/path/to/views.py"),
        class_bases=None,
        methods=["GET", "POST"],
    )

    assert schema.name == "myapp.views.home"
    assert schema.type == "function"
    assert schema.source_path == Path("/path/to/views.py")
    assert schema.class_bases is None
    assert schema.methods == ["GET", "POST"]


def test_view_schema_class():
    schema = ViewSchema(
        name="myapp.views.HomeView",
        type="class",
        source_path=Path("/path/to/views.py"),
        class_bases=["ListView", "LoginRequiredMixin"],
        methods=["GET"],
    )

    assert schema.name == "myapp.views.HomeView"
    assert schema.type == "class"
    assert schema.class_bases == ["ListView", "LoginRequiredMixin"]


def test_route_schema_basic():
    view = ViewSchema(
        name="myapp.views.home",
        type="function",
        source_path=Path("/path/to/views.py"),
        class_bases=None,
        methods=["GET"],
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
    view = ViewSchema(
        name="myapp.views.detail",
        type="function",
        source_path=Path("/path/to/views.py"),
        class_bases=None,
        methods=["GET"],
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
    schema = introspect_view(dummy_function_view)

    assert schema.type == "function"
    assert schema.name.endswith("dummy_function_view")
    assert schema.class_bases is None
    assert "GET" in schema.methods
    assert isinstance(schema.source_path, Path)


def test_introspect_view_class():
    schema = introspect_view(DummyClassView)

    assert schema.type == "class"
    assert schema.name.endswith("DummyClassView")
    assert schema.class_bases == ["View"]
    assert "GET" in schema.methods
    assert isinstance(schema.source_path, Path)


def test_introspect_view_generic():
    schema = introspect_view(DummyListView)

    assert schema.type == "class"
    assert schema.class_bases == ["ListView"]
    assert "GET" in schema.methods


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
    assert isinstance(route.view, ViewSchema)


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

    filtered = filter_routes(routes, method="GET")

    assert len(filtered) > 0
    assert all("GET" in route.view.methods for route in filtered)


def test_filter_routes_multiple_filters():
    routes = get_all_routes()

    if routes:
        filtered = filter_routes(routes, method="GET", pattern=routes[0].pattern[:3])

        assert all("GET" in route.view.methods for route in filtered)
        assert all(routes[0].pattern[:3] in route.pattern for route in filtered)


def test_filter_routes_no_matches():
    routes = get_all_routes()

    filtered = filter_routes(routes, pattern="NONEXISTENT_PATTERN_XYZ123")

    assert filtered == []
