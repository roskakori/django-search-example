from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db import models
from django.utils.translation import gettext_lazy as _

MAX_TITLE_LENGTH = 2048
MAX_AUTHOR_LENGTH = 2048


class Document(models.Model):
    title: str = models.CharField(blank=True, max_length=MAX_TITLE_LENGTH, verbose_name=_("title"))
    language_code: str = models.CharField(
        blank=True,
        max_length=2,
        verbose_name=_("language code"),
        help_text=_('ISO-639-1 language code or "??" if unknown'),
    )
    authors: str = models.CharField(blank=True, max_length=MAX_AUTHOR_LENGTH, verbose_name=_("authors"))
    html: str = models.TextField(blank=True, verbose_name=_("HTML"), help_text=_("Used for display"))
    text: str = models.TextField(blank=True, verbose_name=_("text"), help_text=_("Used for searching"))
    search_vector: SearchVector = SearchVectorField(
        default=None, editable=False, null=True, verbose_name=_("search vector")
    )

    def update_search_vector(self):
        assert self.id is not None, f"{Document.__name__} must be saved before updating the search_vector"
        self.search_vector = SearchVector("text") + SearchVector("title")

    class Meta:
        indexes = [GinIndex(fields=["search_vector"], name="%(app_label)s_doc_search_idx")]  # name <= 30 characters
        verbose_name = _("document")
        verbose_name_plural = _("documents")
