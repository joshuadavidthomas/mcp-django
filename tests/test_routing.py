from __future__ import annotations

from pathlib import Path

from mcp_django.routing import RouteSchema, ViewSchema, get_source_file_path


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
