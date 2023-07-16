from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db import models
from django.db.models import F
from django.utils.translation import gettext_lazy as _

MAX_TITLE_LENGTH = 2048
MAX_AUTHOR_LENGTH = 2048
MAX_SEARCH_CONFIGURATION_LENGTH = 64


class Language(models.TextChoices):
    """
    Language with matching PostgreSQL standard language config.

    OTHER should be mapped to "simple".
    """

    ARABIC = "ar", _("Arabic")
    ARMENIAN = "hy", _("Armenian")
    BASQUE = "eu", _("Basque")
    CATALAN = "ca", _("Catalan")
    DANISH = "da", _("Danish")
    DUTCH = "nl", _("Dutch")
    ENGLISH = "en", _("English")
    FINNISH = "fi", _("Finnish")
    FRENCH = "fr", _("French")
    GERMAN = "de", _("German")
    GREEK = "el", _("Greek")
    HINDI = "hi", _("Hindi")
    HUNGARIAN = "hu", _("Hungarian")
    INDONESIAN = "id", _("Indonesian")
    IRISH = "ga", _("Irish")
    ITALIAN = "it", _("Italian")
    LITHUANIAN = "lt", _("Lithuanian")
    NEPALI = "ne", _("Nepali")
    NORWEGIAN = "no", _("Norwegian")
    PORTUGUESE = "pt", _("Portuguese")
    ROMANIAN = "ro", _("Romanian")
    RUSSIAN = "ru", _("Russian")
    SERBIAN = "sr", _("Serbian")
    SPANISH = "es", _("Spanish")
    SWEDISH = "sv", _("Swedish")
    TAMIL = "ta", _("Tamil")
    TURKISH = "tr", _("Turkish")
    YIDDISH = "yi", _("Yiddish")
    OTHER = "??", _("Other")

    @property
    def config(self) -> str:
        return "simple" if self == self.OTHER else self.name.lower()


class Document(models.Model):
    title: str = models.CharField(blank=True, max_length=MAX_TITLE_LENGTH, verbose_name=_("title"))
    language_code: str = models.CharField(
        choices=Language.choices,
        max_length=2,
        verbose_name=_("language code"),
        help_text=_('ISO-639-1 language code or "??" if unknown'),
    )
    authors: str = models.CharField(blank=True, max_length=MAX_AUTHOR_LENGTH, verbose_name=_("authors"))
    config: str = models.CharField(
        blank=True, default="simple", max_length=MAX_SEARCH_CONFIGURATION_LENGTH, verbose_name=_("search configuration")
    )
    html: str = models.TextField(blank=True, verbose_name=_("HTML"), help_text=_("Used for display"))
    text: str = models.TextField(blank=True, verbose_name=_("text"), help_text=_("Used for searching"))
    search_vector: SearchVector = SearchVectorField(
        default=None, editable=False, null=True, verbose_name=_("search vector")
    )

    def update_search_vector(self):
        assert self.id is not None, f"{Document.__name__} must be saved before updating the search_vector"
        self.search_vector = SearchVector("text", config=F("config"), weight="B") + SearchVector(
            "title", config=F("config"), weight="A"
        )

    class Meta:
        indexes = [GinIndex(fields=["search_vector"], name="%(app_label)s_doc_search_idx")]  # name <= 30 characters
        verbose_name = _("document")
        verbose_name_plural = _("documents")
