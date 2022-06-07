from django.contrib import admin

from gutensearch.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    fields = ("title", "language_code", "authors", "text", "html")
    list_display = ("title", "authors", "language_code")
    list_display_links = ("title",)
    list_filter = ("language_code",)
    search_fields = ("title", "authors", "text")
