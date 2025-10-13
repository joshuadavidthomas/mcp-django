from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.urls import include
from django.urls import path
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods
from django.views.decorators.http import require_POST
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import DetailView
from django.views.generic import ListView


def dummy_view(request):
    pass


@require_GET
def get_only_view(request):
    pass


@require_POST
def post_only_view(request):
    pass


@require_http_methods(["GET", "POST", "PUT"])
def multi_method_view(request):
    pass


@login_required
@require_POST
def protected_post_view(request):
    pass


@cache_page(60)
@require_GET
def cached_get_view(request):
    pass


class BasicView(View):
    def get(self, request):
        pass

    def post(self, request):
        pass


class ArticleDetail(DetailView):
    model = None


class ArticleCreate(CreateView):
    model = None


class ArticleDelete(DeleteView):
    model = None


class ArticleList(ListView):
    model = None


blog_patterns = [
    path("posts/", get_only_view, name="post-list"),
]

api_v1_users_patterns = [
    path("<int:user_id>/", dummy_view, name="user-detail"),
    path("<int:user_id>/posts/", dummy_view, name="user-posts"),
]

api_v1_patterns = [
    path("users/", include((api_v1_users_patterns, "users"), namespace="users")),
]

urlpatterns = [
    path("", dummy_view, name="home"),
    path("get-only/", get_only_view, name="get_only"),
    path("post-only/", post_only_view, name="post_only"),
    path("multi-method/", multi_method_view, name="multi_method"),
    path("protected-post/", protected_post_view, name="protected_post"),
    path("cached-get/", cached_get_view, name="cached_get"),
    path("basic/", BasicView.as_view(), name="basic_view"),
    path("articles/", ArticleList.as_view(), name="article_list"),
    path("articles/<int:pk>/", ArticleDetail.as_view(), name="article_detail"),
    path("articles/create/", ArticleCreate.as_view(), name="article_create"),
    path("articles/<int:pk>/delete/", ArticleDelete.as_view(), name="article_delete"),
    path("items/<slug:slug>/", dummy_view, name="item_by_slug"),
    path(
        "archive/<int:year>/<int:month>/<slug:slug>/",
        dummy_view,
        name="archive_detail",
    ),
    path("blog/", include((blog_patterns, "blog"), namespace="blog")),
    path("api/v1/", include((api_v1_patterns, "v1"), namespace="v1")),
]
