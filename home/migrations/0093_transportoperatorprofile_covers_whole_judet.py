# Generated manually — covers_whole_judet for county-wide transport dispatch

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0092_campanie_discover_hit"),
    ]

    operations = [
        migrations.AddField(
            model_name="transportoperatorprofile",
            name="covers_whole_judet",
            field=models.BooleanField(
                default=False,
                help_text="Dacă e bifat: eligibil pentru orice localitate din județul din profil (nu doar orașul).",
                verbose_name="Acoperă tot județul",
            ),
        ),
    ]
