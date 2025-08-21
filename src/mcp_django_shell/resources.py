from __future__ import annotations

import inspect
import os
import sys
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
    databases: dict[str, dict[str, str | Path]]
    debug: bool
    settings_module: str
    version: tuple[int, int, int, Literal["alpha", "beta", "rc", "final"], int]

    @classmethod
    def from_django(cls) -> DjangoResource:
        app_names = [app_config.name for app_config in apps.get_app_configs()]

        databases = {
            db_alias: {
                "engine": db_config.get("ENGINE", ""),
                "name": db_config.get("NAME", ""),
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
            base_dir=Path(settings.BASE_DIR)
            if hasattr(settings, "BASE_DIR")
            else Path.cwd(),
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
        try:
            appconfig = get_source_file_path(app)
            app_path = Path(appconfig).parent
        except (TypeError, OSError):
            app_path = Path("unknown")

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
        try:
            source_file = get_source_file_path(model)
            source_path = Path(source_file)
        except (TypeError, OSError):
            source_path = Path("unknown")

        field_types = {
            field.name: field.__class__.__name__ for field in model._meta.fields
        }

        return cls(
            model_class=model,
            import_path=f"{model.__module__}.{model.__name__}",
            source_path=source_path,
            fields=field_types,
        )

    @field_serializer("model_class")
    def serialize_model_class(self, klass: type[models.Model]) -> str:
        return klass.__name__
