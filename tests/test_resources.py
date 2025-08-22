from __future__ import annotations

import sys
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import override_settings

from mcp_django.resources import AppResource
from mcp_django.resources import DjangoResource
from mcp_django.resources import ModelResource
from mcp_django.resources import ProjectResource
from mcp_django.resources import PythonResource
from mcp_django.resources import get_source_file_path
from tests.models import AModel


def test_get_source_file_path_with_class():
    result = get_source_file_path(AModel)
    assert isinstance(result, Path)
    assert result != Path("unknown")


def test_get_source_file_path_with_instance():
    result = get_source_file_path(AModel())
    assert isinstance(result, Path)
    assert result != Path("unknown")


def test_get_source_file_path_unknown():
    # Built-in types like int don't have source files, so this should trigger the exception path
    result = get_source_file_path(42)
    assert isinstance(result, Path)
    assert result == Path("unknown")


def test_get_source_file_path_valueerror(monkeypatch):
    mock_obj = object()

    monkeypatch.setattr(
        "mcp_django.resources.inspect.getfile",
        lambda obj: "/usr/lib/python3.12/os.py",
    )
    monkeypatch.setattr(
        "mcp_django.resources.Path.cwd",
        lambda: Path("/completely/different/path"),
    )

    result = get_source_file_path(mock_obj)
    assert str(result) == "/usr/lib/python3.12/os.py"


def test_project_resource_from_env():
    result = ProjectResource.from_env()

    assert isinstance(result.python, PythonResource)
    assert isinstance(result.django, DjangoResource)

    data = result.model_dump()
    assert "python" in data
    assert "django" in data


def test_python_resource_from_sys():
    result = PythonResource.from_sys()

    assert result.base_prefix == Path(sys.base_prefix)
    assert result.executable == Path(sys.executable)
    assert result.path == [Path(p) for p in sys.path]
    assert result.platform == sys.platform
    assert result.prefix == Path(sys.prefix)
    assert result.version_info == sys.version_info


@override_settings(
    INSTALLED_APPS=settings.INSTALLED_APPS
    + [
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]
)
def test_django_resource_from_django():
    result = DjangoResource.from_django()

    assert isinstance(result.apps, list)
    assert len(result.apps) > 0
    assert "django.contrib.auth" in result.apps
    assert result.auth_user_model is not None  # Should have auth user model
    assert isinstance(result.base_dir, Path)
    assert isinstance(result.databases, dict)
    assert isinstance(result.debug, bool)
    assert isinstance(result.settings_module, str)
    assert isinstance(result.version, tuple)

    data = result.model_dump()

    assert "apps" in data
    assert "databases" in data


def test_django_resource_without_auth():
    result = DjangoResource.from_django()
    assert result.auth_user_model is None


def test_django_resource_without_base_dir(monkeypatch):
    monkeypatch.delattr(settings, "BASE_DIR", raising=False)
    resource = DjangoResource.from_django()
    assert resource.base_dir == Path.cwd()


@override_settings(
    DATABASES={
        "sqlite": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": Path("/tmp/db.sqlite3"),
        },
        "postgres": {"ENGINE": "django.db.backends.postgresql", "NAME": "mydb"},
    }
)
def test_django_resource_mixed_databases():
    resource = DjangoResource.from_django()
    assert isinstance(resource.databases["sqlite"]["name"], str)
    assert isinstance(resource.databases["postgres"]["name"], str)


@override_settings(DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3"}})
def test_django_resource_missing_db_name():
    resource = DjangoResource.from_django()
    assert resource.databases["default"]["name"] == ""


def test_app_resource_from_app():
    tests_app = apps.get_app_config("tests")

    result = AppResource.from_app(tests_app)

    assert result.name == "tests"
    assert result.label == "tests"
    assert isinstance(result.path, Path)
    assert isinstance(result.models, list)
    assert len(result.models) > 0

    data = result.model_dump()

    assert isinstance(data["models"], list)
    assert all(isinstance(model_class, str) for model_class in data["models"])
    assert len(data["models"]) > 0


def test_model_resource_from_model():
    result = ModelResource.from_model(AModel)

    assert result.model_class == AModel
    assert result.import_path == "tests.models.AModel"
    assert isinstance(result.source_path, Path)
    assert isinstance(result.fields, dict)
    assert "name" in result.fields
    assert "value" in result.fields
    assert "created_at" in result.fields

    data = result.model_dump()

    assert data["model_class"] == "AModel"
