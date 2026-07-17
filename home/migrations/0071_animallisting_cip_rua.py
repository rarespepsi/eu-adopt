from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0070_shelter_public_slugs"),
    ]

    operations = [
        migrations.AddField(
            model_name="animallisting",
            name="cip_rua",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Număr microcip sau RUA (când animalul are CIP).",
                max_length=30,
                verbose_name="CIP/RUA",
            ),
        ),
    ]
