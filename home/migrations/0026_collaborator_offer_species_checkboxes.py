from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0025_collaborator_offer_product_sheet"),
    ]

    operations = [
        migrations.AddField(
            model_name="collaboratorserviceoffer",
            name="species_cat",
            field=models.BooleanField(default=True, verbose_name="Specie: pisică"),
        ),
        migrations.AddField(
            model_name="collaboratorserviceoffer",
            name="species_dog",
            field=models.BooleanField(default=True, verbose_name="Specie: câine"),
        ),
        migrations.AddField(
            model_name="collaboratorserviceoffer",
            name="species_other",
            field=models.BooleanField(default=True, verbose_name="Specie: altele"),
        ),
    ]
