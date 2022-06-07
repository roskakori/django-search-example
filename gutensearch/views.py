import time
from typing import Any, Dict, Optional

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.core.exceptions import BadRequest, ValidationError
from django.db import connection
from django.db.models import F, QuerySet
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode

from gutensearch.forms import SearchForm
from gutensearch.models import Document


def search_query_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SearchForm(request.POST)
        if form.is_valid():
            search_term = form.cleaned_data.get("search_term")
            try:
                parameters = {"search_term": search_term}
                return redirect(reverse_with_parameters("search_result", parameters))
            except ValidationError as error:
                form.add_error("search_term", error)
    else:
        form = SearchForm()
    return render(
        request,
        "gutensearch/search_query.html",
        {
            "form": form,
        },
    )


def search_result_view(request: HttpRequest) -> HttpResponse:
    form = SearchForm(request.GET)
    if not form.is_valid():
        raise BadRequest()
    search_term = form.cleaned_data["search_term"]
    search_start_time = time.time()
    documents = documents_matching(search_term)[:20]
    search_duration_in_ms = (time.time() - search_start_time) * 1000
    search_expression = to_tsquery(search_term)
    return render(
        request,
        "gutensearch/search_result.html",
        {
            "documents": documents,
            "search_duration_in_ms": search_duration_in_ms,
            "search_expression": search_expression,
            "search_term": search_term,
        },
    )


def to_tsquery(search_term: str) -> str:
    with connection.cursor() as cursor:
        cursor.execute("select to_tsquery(%s, %s)", ["german", search_term])
        (result,) = cursor.fetchone()
    return result


def documents_matching(search_term: str) -> QuerySet[Document]:
    search_query = SearchQuery(search_term, search_type="raw")
    search_rank = SearchRank(F("search_vector"), search_query)
    return (
        Document.objects.annotate(
            rank=search_rank,
        )
        .filter(search_vector=search_query)
        .order_by("-rank")
    )


def reverse_with_parameters(view_name: str, parameters: Dict[str, Optional[Any]]) -> str:
    return f"{reverse(view_name)}?{urlencode(parameters)}"


def document_view(request: HttpRequest, pk: Optional[int] = None) -> HttpResponse:
    document = get_object_or_404(Document, pk=pk)
    return render(request, "gutensearch/document.html", {"html": document.html})
