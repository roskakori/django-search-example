import django.contrib.postgres.indexes
import django.contrib.postgres.search
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("gutensearch", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="search_vector",
            field=django.contrib.postgres.search.SearchVectorField(
                default=None, editable=False, null=True, verbose_name="search vector"
            ),
        ),
        migrations.AddIndex(
            model_name="document",
            index=django.contrib.postgres.indexes.GinIndex(fields=["search_vector"], name="gutensearch_doc_search_idx"),
        ),
    ]
