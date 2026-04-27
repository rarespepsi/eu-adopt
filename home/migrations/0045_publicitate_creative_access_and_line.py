# Generated manually for publicitate post-pay creative flow

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0044_sitecartitem_kind_publicitate"),
    ]

    operations = [
        migrations.CreateModel(
            name="PublicitateOrderCreativeAccess",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("secret_token", models.CharField(db_index=True, max_length=64, unique=True, verbose_name="Token acces")),
                ("expires_at", models.DateTimeField(verbose_name="Expiră la")),
                ("email_sent_at", models.DateTimeField(blank=True, null=True, verbose_name="Email trimis la")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="creative_access",
                        to="home.publicitateorder",
                    ),
                ),
            ],
            options={
                "verbose_name": "Acces materiale publicitate (comandă)",
                "verbose_name_plural": "Acces materiale publicitate",
            },
        ),
        migrations.CreateModel(
            name="PublicitateLineCreative",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to="pub_creative/%Y/%m/",
                        verbose_name="Imagine banner",
                    ),
                ),
                ("external_link", models.CharField(blank=True, default="", max_length=500, verbose_name="Link țintă (https)")),
                ("extra_notes", models.TextField(blank=True, default="", verbose_name="Detalii / text reclamă")),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "În așteptare încărcare"), ("live", "Încărcat / aplicat pe site")],
                        db_index=True,
                        default="pending",
                        max_length=16,
                        verbose_name="Status",
                    ),
                ),
                ("submitted_at", models.DateTimeField(blank=True, null=True, verbose_name="Trimis la")),
                ("live_at", models.DateTimeField(blank=True, null=True, verbose_name="Live pe site la")),
                (
                    "review_until",
                    models.DateTimeField(
                        blank=True,
                        help_text="După încărcare: fereastră recomandată pentru verificare (ex. +12h).",
                        null=True,
                        verbose_name="Verificare staff până la",
                    ),
                ),
                (
                    "line",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="creative_bundle",
                        to="home.publicitateorderline",
                    ),
                ),
            ],
            options={
                "verbose_name": "Materiale creative linie publicitate",
                "verbose_name_plural": "Materiale creative linii publicitate",
            },
        ),
    ]
