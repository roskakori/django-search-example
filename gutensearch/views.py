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
    documents = documents_matching(search_term)[:20]
    return render(
        request,
        "gutensearch/search_result.html",
        {
            "documents": documents,
            "search_term": search_term,
        },
    )


def documents_matching(search_term: str) -> QuerySet[Document]:
    return Document.objects.filter(Q(title__icontains=search_term) | Q(text__icontains=search_term)).order_by("id")


def reverse_with_parameters(view_name: str, parameters: Dict[str, Optional[Any]]) -> str:
    return f"{reverse(view_name)}?{urlencode(parameters)}"


def document_view(request: HttpRequest, pk: Optional[int] = None) -> HttpResponse:
    document = get_object_or_404(Document, pk=pk)
    return render(request, "gutensearch/document.html", {"html": document.html})
