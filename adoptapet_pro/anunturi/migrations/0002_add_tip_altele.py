# Generated manually for Altele (completare + verificare)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("anunturi", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="pet",
            name="tip_altele",
            field=models.CharField(
                blank=True,
                choices=[
                    ("bird", "Pasăre"),
                    ("donkey", "Magar"),
                    ("rabbit", "Iepure"),
                    ("hamster", "Hamster"),
                    ("guinea_pig", "Cobai"),
                    ("other", "Altul (completați mai jos)"),
                ],
                help_text="Obligatoriu dacă Tip = Altele. Alege din listă sau Altul.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="pet",
            name="tip_altele_altul",
            field=models.CharField(
                blank=True,
                help_text="Doar dacă la „Altele” ați ales „Altul”. Ex: Șopârlă. Max 80 caractere, doar litere/spații.",
                max_length=80,
            ),
        ),
    ]
