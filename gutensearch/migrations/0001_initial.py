from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Document",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(blank=True, max_length=2048, verbose_name="title")),
                (
                    "language_code",
                    models.CharField(
                        blank=True,
                        help_text='ISO-639-1 language code or "??" if unknown',
                        max_length=2,
                        verbose_name="language code",
                    ),
                ),
                ("authors", models.CharField(blank=True, max_length=2048, verbose_name="authors")),
                ("html", models.TextField(blank=True, help_text="Used for display", verbose_name="HTML")),
                ("text", models.TextField(blank=True, help_text="Used for searching", verbose_name="text")),
            ],
            options={
                "verbose_name": "document",
                "verbose_name_plural": "documents",
            },
        ),
    ]
