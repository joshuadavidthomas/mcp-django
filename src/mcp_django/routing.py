from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class ViewSchema(BaseModel):
    name: str
    type: Literal["function", "class"]
    source_path: Path
    class_bases: list[str] | None
    methods: list[str]


class RouteSchema(BaseModel):
    pattern: str
    name: str | None
    namespace: str | None
    parameters: list[str]
    view: ViewSchema
