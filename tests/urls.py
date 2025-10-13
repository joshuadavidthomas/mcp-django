from __future__ import annotations

from django.urls import include
from django.urls import path
from django.views.decorators.http import require_GET


def dummy_view(request):
    pass


@require_GET
def get_only_view(request):
    pass


blog_patterns = [
    path("posts/", get_only_view, name="post-list"),
]

urlpatterns = [
    path("", dummy_view, name="home"),
    path("get-only/", get_only_view, name="get_only"),
    path("blog/", include((blog_patterns, "blog"), namespace="blog")),
]
