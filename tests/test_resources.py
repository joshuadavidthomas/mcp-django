from __future__ import annotations

import sys
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import override_settings

from mcp_django.project.resources import AppResource
from mcp_django.project.resources import DjangoResource
from mcp_django.project.resources import ModelResource
from mcp_django.project.resources import ProjectResource
from mcp_django.project.resources import PythonResource
from mcp_django.project.resources import SettingResource
from mcp_django.project.resources import get_source_file_path
from mcp_django.project.resources import is_first_party_app
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
        "mcp_django.project.resources.inspect.getfile",
        lambda obj: "/usr/lib/python3.12/os.py",
    )
    monkeypatch.setattr(
        "mcp_django.project.resources.Path.cwd",
        lambda: Path("/completely/different/path"),
    )

    result = get_source_file_path(mock_obj)
    assert str(result) == "/usr/lib/python3.12/os.py"


def test_is_first_party_app_first_party():
    """Test that project apps are correctly identified as first-party."""
    tests_app = apps.get_app_config("tests")
    result = is_first_party_app(tests_app)
    assert result is True


@override_settings(
    INSTALLED_APPS=settings.INSTALLED_APPS
    + ["django.contrib.auth", "django.contrib.contenttypes"]
)
def test_is_first_party_app_third_party():
    """Test that Django built-in apps are correctly identified as third-party."""
    auth_app = apps.get_app_config("auth")
    result = is_first_party_app(auth_app)
    assert result is False


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


def test_setting_resource_with_bool():
    result = SettingResource(key="DEBUG", value=False, value_type="bool")

    assert result.key == "DEBUG"
    assert result.value is False
    assert result.value_type == "bool"

    data = result.model_dump()
    assert data["value"] is False


def test_setting_resource_with_list():
    apps = ["django.contrib.auth", "myapp"]
    result = SettingResource(key="INSTALLED_APPS", value=apps, value_type="list")

    assert result.key == "INSTALLED_APPS"
    assert result.value == apps
    assert result.value_type == "list"


def test_setting_resource_with_dict():
    databases = {"default": {"ENGINE": "django.db.backends.sqlite3"}}
    result = SettingResource(key="DATABASES", value=databases, value_type="dict")

    assert result.key == "DATABASES"
    assert result.value == databases
    assert result.value_type == "dict"


def test_setting_resource_serializes_path():
    from pathlib import Path

    base_dir = Path("/home/user/project")
    result = SettingResource(key="BASE_DIR", value=base_dir, value_type="PosixPath")

    data = result.model_dump()
    assert data["value"] == "/home/user/project"
    assert isinstance(data["value"], str)


def test_setting_resource_serializes_class():
    # Use AModel from tests since it doesn't require extra apps installed
    result = SettingResource(key="SOME_MODEL_CLASS", value=AModel, value_type="type")

    data = result.model_dump()
    assert data["value"] == "tests.models.AModel"
    assert isinstance(data["value"], str)
