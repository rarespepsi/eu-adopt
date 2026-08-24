# Generated manually — only LostFoundAnimal (fără rename-uri de index stray)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0085_media_outreach_invite_controls"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LostFoundAnimal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kind",
                    models.CharField(
                        choices=[("pierdut", "Pierdut"), ("gasit", "Găsit")],
                        db_index=True,
                        max_length=12,
                        verbose_name="Tip",
                    ),
                ),
                (
                    "species",
                    models.CharField(
                        choices=[("dog", "Câine"), ("cat", "Pisică"), ("other", "Alt")],
                        default="dog",
                        max_length=12,
                        verbose_name="Specie",
                    ),
                ),
                ("name", models.CharField(blank=True, default="", max_length=80, verbose_name="Nume (opțional)")),
                ("judet", models.CharField(db_index=True, max_length=64, verbose_name="Județ")),
                ("judet_slug", models.CharField(db_index=True, max_length=80, verbose_name="Slug județ")),
                ("localitate", models.CharField(max_length=120, verbose_name="Localitate")),
                ("description", models.TextField(max_length=2000, verbose_name="Detalii")),
                ("photo", models.ImageField(upload_to="pierdute/%Y/%m/", verbose_name="Poză")),
                ("phone", models.CharField(blank=True, default="", max_length=32, verbose_name="Telefon contact")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Activ")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lost_found_animals",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Animal pierdut/găsit",
                "verbose_name_plural": "Animale pierdute/găsite",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="lostfoundanimal",
            index=models.Index(fields=["judet_slug", "is_active", "-created_at"], name="home_lostfo_judet_s_d9d685_idx"),
        ),
        migrations.AddIndex(
            model_name="lostfoundanimal",
            index=models.Index(fields=["kind", "is_active"], name="home_lostfo_kind_49862e_idx"),
        ),
    ]
