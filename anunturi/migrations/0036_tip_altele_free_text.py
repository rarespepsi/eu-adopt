# Tip_altele devine câmp text liber (fără listă fixă); userul completează ce tip de animal e (ex: Pasăre, Șopârlă).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("anunturi", "0035_add_varsta_aproximativa"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pet",
            name="tip_altele",
            field=models.CharField(
                blank=True,
                help_text="Completați liber dacă Tip = Altele (ex: Pasăre, Iepure, Șopârlă). În liste apare la categoria Altele.",
                max_length=80,
                verbose_name="Tip animal (Altele)",
            ),
        ),
    ]
