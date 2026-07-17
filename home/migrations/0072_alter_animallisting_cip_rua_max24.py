from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0071_animallisting_cip_rua"),
    ]

    operations = [
        migrations.AlterField(
            model_name="animallisting",
            name="cip_rua",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Număr microcip sau RUA (max. 24 cifre).",
                max_length=24,
                verbose_name="CIP/RUA",
            ),
        ),
    ]
