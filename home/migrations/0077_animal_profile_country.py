from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0076_reclamaslotnote_market"),
    ]

    operations = [
        migrations.AddField(
            model_name="animallisting",
            name="country",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="RO",
                help_text="ISO 3166-1 alpha-2 (ex. RO, DE). Implicit România.",
                max_length=2,
                verbose_name="Țară",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="country",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="RO",
                help_text="ISO 3166-1 alpha-2. Implicit România.",
                max_length=2,
                verbose_name="Țară",
            ),
        ),
    ]
