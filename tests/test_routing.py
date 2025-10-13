from __future__ import annotations

from pathlib import Path

from mcp_django.routing import ViewSchema


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
