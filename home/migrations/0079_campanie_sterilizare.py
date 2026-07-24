from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("home", "0078_transport_request_country"),
    ]

    operations = [
        migrations.CreateModel(
            name="CampanieSterilizare",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("judet", models.CharField(db_index=True, max_length=64, verbose_name="Județ")),
                ("judet_slug", models.CharField(db_index=True, max_length=80, verbose_name="Slug județ")),
                ("localitate", models.CharField(max_length=120, verbose_name="Localitate")),
                ("species_dogs", models.BooleanField(default=False, verbose_name="Câini")),
                ("species_cats", models.BooleanField(default=False, verbose_name="Pisici")),
                ("date_start", models.DateField(verbose_name="Început")),
                ("date_end", models.DateField(verbose_name="Sfârșit")),
                ("photo", models.ImageField(upload_to="campanii/%Y/%m/", verbose_name="Poză / afiș")),
                (
                    "link",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="URL opțional (FB / Insta / site campanie).",
                        max_length=500,
                        verbose_name="Link campanie",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="campanii_sterilizare",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Campanie sterilizare",
                "verbose_name_plural": "Campanii sterilizare",
                "ordering": ["localitate", "-date_start", "-pk"],
                "indexes": [
                    models.Index(fields=["judet_slug", "date_end"], name="home_campan_judet_s_7c1a2b_idx"),
                    models.Index(fields=["date_end"], name="home_campan_date_en_8d3e4f_idx"),
                ],
            },
        ),
    ]
