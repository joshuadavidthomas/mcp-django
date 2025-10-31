from __future__ import annotations

import inspect
import os
import sys
import sysconfig
from pathlib import Path
from typing import Any
from typing import Literal

import django
from django.apps import AppConfig
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from pydantic import BaseModel
from pydantic import field_serializer


def get_source_file_path(obj: Any) -> Path:
    target = obj if inspect.isclass(obj) else obj.__class__
    try:
        return Path(inspect.getfile(target))
    except (TypeError, OSError):
        return Path("unknown")


def is_first_party_app(app_config: AppConfig) -> bool:
    """Check if an app is first-party (project code) vs third-party (installed package).

    Uses Python's sysconfig to determine installation paths, which properly handles
    all installation scenarios (pip, conda, virtualenv, etc.) and is platform-independent.

    Args:
        app_config: Django AppConfig to check

    Returns:
        True if the app is first-party project code, False if third-party or stdlib
    """
    try:
        app_path = Path(inspect.getfile(app_config.module)).resolve()

        for lib_path in [
            Path(sysconfig.get_path("purelib")),  # site-packages (pure Python)
            Path(sysconfig.get_path("platlib")),  # site-packages (platform-specific)
            Path(sysconfig.get_path("stdlib")),  # standard library
        ]:
            try:
                if app_path.is_relative_to(lib_path):
                    return False
            except ValueError:
                # Path is on a different drive/mount (Windows), definitely not relative
                pass

        return True
    except (TypeError, OSError):
        return False


def filter_models(
    models: list[Any],
    include: list[str] | None = None,
    scope: Literal["project", "all"] = "project",
) -> list[Any]:
    """Filter Django models by app inclusion or scope.

    Args:
        models: List of Django model classes to filter
        include: Specific app labels to include (overrides scope)
        scope: "project" for project models, "all" for everything

    Returns:
        Filtered list of model classes
    """
    filtered_models = []

    for model in models:
        app_label = model._meta.app_label

        # If include is specified, only filter by include (ignore scope)
        if include is not None:
            if app_label in include:
                filtered_models.append(model)
        # Otherwise, filter by scope
        elif scope == "project" and is_first_party_app(apps.get_app_config(app_label)):
            filtered_models.append(model)
        elif scope == "all":
            filtered_models.append(model)

    return filtered_models


class ProjectResource(BaseModel):
    python: PythonResource
    django: DjangoResource

    @classmethod
    def from_env(cls) -> ProjectResource:
        py = PythonResource.from_sys()
        dj = DjangoResource.from_django()
        return ProjectResource(python=py, django=dj)


class PythonResource(BaseModel):
    base_prefix: Path
    executable: Path
    path: list[Path]
    platform: str
    prefix: Path
    version_info: tuple[
        int, int, int, Literal["alpha", "beta", "candidate", "final"], int
    ]

    @classmethod
    def from_sys(cls) -> PythonResource:
        return cls(
            base_prefix=Path(sys.base_prefix),
            executable=Path(sys.executable),
            path=[Path(p) for p in sys.path],
            platform=sys.platform,
            prefix=Path(sys.prefix),
            version_info=sys.version_info,
        )


class DjangoResource(BaseModel):
    apps: list[str]
    auth_user_model: str | None
    base_dir: Path
    databases: dict[str, dict[str, str]]
    debug: bool
    settings_module: str
    version: tuple[int, int, int, Literal["alpha", "beta", "rc", "final"], int]

    @classmethod
    def from_django(cls) -> DjangoResource:
        app_names = [app_config.name for app_config in apps.get_app_configs()]

        databases = {
            db_alias: {
                "engine": db_config.get("ENGINE", ""),
                "name": str(db_config.get("NAME", "")),
            }
            for db_alias, db_config in settings.DATABASES.items()
        }

        if "django.contrib.auth" in app_names:
            user_model = get_user_model()
            auth_user_model = f"{user_model.__module__}.{user_model.__name__}"
        else:
            auth_user_model = None

        return cls(
            apps=app_names,
            auth_user_model=auth_user_model,
            base_dir=Path(getattr(settings, "BASE_DIR", Path.cwd())),
            databases=databases,
            debug=settings.DEBUG,
            settings_module=os.environ.get("DJANGO_SETTINGS_MODULE", ""),
            version=django.VERSION,
        )


class AppResource(BaseModel):
    name: str
    label: str
    path: Path
    models: list[ModelResource]

    @classmethod
    def from_app(cls, app: AppConfig) -> AppResource:
        appconfig = get_source_file_path(app)
        app_path = appconfig.parent if appconfig != Path("unknown") else Path("unknown")

        app_models = (
            [
                ModelResource.from_model(model)
                for model in app.models.values()
                if not model._meta.auto_created
            ]
            if app.models
            else []
        )

        return cls(name=app.name, label=app.label, path=app_path, models=app_models)

    @field_serializer("models")
    def serialize_models(self, models: list[ModelResource]) -> list[str]:
        return [model.model_dump()["model_class"] for model in models]


class ModelResource(BaseModel):
    model_class: type[models.Model]
    import_path: str
    source_path: Path
    fields: dict[str, str]

    @classmethod
    def from_model(cls, model: type[models.Model]):
        field_types = {
            field.name: field.__class__.__name__ for field in model._meta.fields
        }

        return cls(
            model_class=model,
            import_path=f"{model.__module__}.{model.__name__}",
            source_path=get_source_file_path(model),
            fields=field_types,
        )

    @field_serializer("model_class")
    def serialize_model_class(self, klass: type[models.Model]) -> str:
        return klass.__name__


class SettingResource(BaseModel):
    key: str
    value: Any
    value_type: str

    @field_serializer("value")
    def serialize_value(self, value: Any) -> Any:
        # Handle common Django types that need conversion
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, type):  # Class objects
            return f"{value.__module__}.{value.__name__}"
        return value
