from typing import Any, Dict, Optional

from django.contrib.postgres.search import SearchHeadline, SearchQuery, SearchRank
from django.core.exceptions import BadRequest
from django.db import connection
from django.db.models import F, QuerySet, Value
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode

from gutensearch.forms import SearchForm
from gutensearch.models import Document

_SEARCH_HEADLINE_SELECTION_START = '<span style="background-color: lightgreen">'
_SEARCH_HEADLINE_SELECTION_STOP = "</span>"


def search_query_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SearchForm(request.POST)
        if form.is_valid():
            search_term = form.cleaned_data.get("search_term")
            parameters = {"search_term": search_term}
            return redirect(reverse_with_parameters("search_result", parameters))
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
        raise BadRequest(f"form must be valid: {form.errors}")
    search_term = form.cleaned_data["search_term"]
    documents = documents_matching(search_term)[:20]
    search_expression = to_tsquery(search_term)
    return render(
        request,
        "gutensearch/search_result.html",
        {
            "documents": documents,
            "search_expression": search_expression,
            "search_term": search_term,
        },
    )


def to_tsquery(search_term: str) -> str:
    with connection.cursor() as cursor:
        cursor.execute("select to_tsquery(%s, %s)", ["simple", search_term])
        (result,) = cursor.fetchone()
    return result


def documents_matching(search_term: str) -> QuerySet[Document]:
    search_query = SearchQuery(search_term, search_type="raw")
    # Normalization=1 divides the rank by 1 + the logarithm of the document length.
    search_rank = SearchRank(F("search_vector"), search_query, normalization=Value(1))
    return (
        Document.objects.annotate(
            rank=search_rank,
            search_headline_text=SearchHeadline(
                "text",
                search_query,
                min_words=50,
                max_words=150,
                start_sel=_SEARCH_HEADLINE_SELECTION_START,
                stop_sel=_SEARCH_HEADLINE_SELECTION_STOP,
            ),
            search_headline_title=SearchHeadline(
                "title",
                search_query,
                min_words=999,
                max_words=1000,
                start_sel=_SEARCH_HEADLINE_SELECTION_START,
                stop_sel=_SEARCH_HEADLINE_SELECTION_STOP,
            ),
        )
        .filter(search_vector=search_query)
        .order_by("-rank")
    )


def reverse_with_parameters(view_name: str, parameters: Dict[str, Optional[Any]]) -> str:
    return f"{reverse(view_name)}?{urlencode(parameters)}"


def document_view(request: HttpRequest, pk: Optional[int] = None) -> HttpResponse:
    document = get_object_or_404(Document, pk=pk)
    return render(request, "gutensearch/document.html", {"html": document.html})
