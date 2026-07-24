from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0077_animal_profile_country"),
    ]

    operations = [
        migrations.AddField(
            model_name="transportveterinaryrequest",
            name="country",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="RO",
                help_text="ISO 3166-1 alpha-2 (ex. RO, DE).",
                max_length=2,
                verbose_name="Țară",
            ),
        ),
    ]
