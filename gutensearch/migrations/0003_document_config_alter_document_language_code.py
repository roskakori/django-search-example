from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gutensearch", "0002_document_search_vector_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="config",
            field=models.CharField(blank=True, default="simple", max_length=64, verbose_name="search configuration"),
        ),
        migrations.AlterField(
            model_name="document",
            name="language_code",
            field=models.CharField(
                choices=[
                    ("ar", "Arabic"),
                    ("hy", "Armenian"),
                    ("eu", "Basque"),
                    ("ca", "Catalan"),
                    ("da", "Danish"),
                    ("nl", "Dutch"),
                    ("en", "English"),
                    ("fi", "Finnish"),
                    ("fr", "French"),
                    ("de", "German"),
                    ("el", "Greek"),
                    ("hi", "Hindi"),
                    ("hu", "Hungarian"),
                    ("id", "Indonesian"),
                    ("ga", "Irish"),
                    ("it", "Italian"),
                    ("lt", "Lithuanian"),
                    ("ne", "Nepali"),
                    ("no", "Norwegian"),
                    ("pt", "Portuguese"),
                    ("ro", "Romanian"),
                    ("ru", "Russian"),
                    ("sr", "Serbian"),
                    ("es", "Spanish"),
                    ("sv", "Swedish"),
                    ("ta", "Tamil"),
                    ("tr", "Turkish"),
                    ("yi", "Yiddish"),
                    ("??", "Other"),
                ],
                help_text='ISO-639-1 language code or "??" if unknown',
                max_length=2,
                verbose_name="language code",
            ),
        ),
    ]
