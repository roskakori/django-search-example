from django import forms
from django.utils.translation import gettext_lazy as _

MIN_SEARCH_TERM_LENGTH = 3
MAX_SEARCH_TERM_LENGTH = 1000


class SearchForm(forms.Form):
    search_term = forms.CharField(
        label=_("Search term"),
        localize=True,
        min_length=MIN_SEARCH_TERM_LENGTH,
        max_length=MAX_SEARCH_TERM_LENGTH,
    )
