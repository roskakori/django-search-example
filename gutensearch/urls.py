from django.urls import path

from gutensearch.views import document_view, language_statistics_view, search_query_view, search_result_view

urlpatterns = [
    path("document/<int:pk>/", document_view, name="document"),
    path("language_statistics/", language_statistics_view, name="language_statistics"),
    path("search/", search_result_view, name="search_result"),
    path("", search_query_view, name="search_query"),
]
