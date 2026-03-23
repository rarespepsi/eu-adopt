# Generated manually for target filters on collaborator offers

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0023_collaborator_offer_external_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="collaboratorserviceoffer",
            name="target_species",
            field=models.CharField(
                choices=[
                    ("all", "Câine sau pisică (oricare)"),
                    ("dog", "Câine"),
                    ("cat", "Pisică"),
                ],
                db_index=True,
                default="all",
                max_length=12,
                verbose_name="Țintă: specie",
            ),
        ),
        migrations.AddField(
            model_name="collaboratorserviceoffer",
            name="target_size",
            field=models.CharField(
                choices=[
                    ("all", "Oricare talie"),
                    ("small", "Talie mică"),
                    ("medium", "Talie medie"),
                    ("large", "Talie mare"),
                ],
                default="all",
                max_length=12,
                verbose_name="Țintă: talie (în special câine)",
            ),
        ),
        migrations.AddField(
            model_name="collaboratorserviceoffer",
            name="target_sex",
            field=models.CharField(
                choices=[
                    ("all", "Oricare sex"),
                    ("male", "Mascul"),
                    ("female", "Femelă"),
                ],
                default="all",
                max_length=12,
                verbose_name="Țintă: sex",
            ),
        ),
        migrations.AddField(
            model_name="collaboratorserviceoffer",
            name="target_age_band",
            field=models.CharField(
                choices=[
                    ("all", "Oricare vârstă"),
                    ("puppy", "Pui"),
                    ("young", "Tânăr"),
                    ("adult", "Adult"),
                    ("senior", "Senior"),
                ],
                default="all",
                max_length=12,
                verbose_name="Țintă: categorie vârstă",
            ),
        ),
        migrations.AddField(
            model_name="collaboratorserviceoffer",
            name="target_sterilized",
            field=models.CharField(
                choices=[
                    ("all", "Oricare"),
                    ("yes", "Sterilizat / castrat"),
                    ("no", "Nesterilizat"),
                ],
                default="all",
                max_length=12,
                verbose_name="Țintă: sterilizare",
            ),
        ),
    ]
