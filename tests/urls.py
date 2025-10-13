from __future__ import annotations

from django.urls import path


def dummy_view(request):
    pass


urlpatterns = [
    path("", dummy_view, name="home"),
]
