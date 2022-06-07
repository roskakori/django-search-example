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

    class Meta:
        verbose_name = _("document")
        verbose_name_plural = _("documents")
