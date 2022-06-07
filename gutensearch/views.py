import time
from typing import Any, Dict, Optional

from django.core.exceptions import BadRequest, ValidationError
from django.db.models import Q, QuerySet
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
            search_query = form.cleaned_data.get("search_query")
            try:
                parameters = {"search_query": search_query}
                return redirect(reverse_with_parameters("search_result", parameters))
            except ValidationError as error:
                form.add_error("search_query", error)
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
    search_query = form.cleaned_data["search_query"]
    search_start_time = time.time()
    documents = documents_matching(search_query)[:20]
    search_duration_in_ms = (time.time() - search_start_time) * 1000
    return render(
        request,
        "gutensearch/search_result.html",
        {
            "documents": documents,
            "search_duration_in_ms": search_duration_in_ms,
            "search_query": search_query,
        },
    )


def documents_matching(search_query: str) -> QuerySet[Document]:
    return Document.objects.filter(Q(title__icontains=search_query) | Q(text__icontains=search_query)).order_by("id")


def reverse_with_parameters(view_name: str, parameters: Dict[str, Optional[Any]]) -> str:
    return f"{reverse(view_name)}?{urlencode(parameters)}"


def document_view(request: HttpRequest, pk: Optional[int] = None) -> HttpResponse:
    document = get_object_or_404(Document, pk=pk)
    return render(request, "gutensearch/document.html", {"html": document.html})
