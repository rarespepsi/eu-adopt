# Generated manually for TransportOperatorProfile

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0035_transport_veterinary_request"),
    ]

    operations = [
        migrations.CreateModel(
            name="TransportOperatorProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "approval_status",
                    models.CharField(
                        choices=[
                            ("pending", "În așteptare aprobare"),
                            ("approved", "Aprobat"),
                            ("inactive", "Inactiv"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                        verbose_name="Status aprobare",
                    ),
                ),
                ("transport_national", models.BooleanField(default=False, verbose_name="TRANSPORT NAȚIONAL")),
                ("transport_international", models.BooleanField(default=False, verbose_name="TRANSPORT INTERNATIONAL")),
                ("max_caini", models.PositiveSmallIntegerField(default=1, verbose_name="Capacitate max. câini / cursă")),
                ("max_pisici", models.PositiveSmallIntegerField(default=1, verbose_name="Capacitate max. pisici / cursă")),
                ("block_count", models.PositiveSmallIntegerField(default=0, verbose_name="Număr blocări")),
                ("blocked_until", models.DateTimeField(blank=True, null=True, verbose_name="Blocat până la")),
                ("removed_after_third_block", models.BooleanField(default=False, verbose_name="Eliminat după a 3-a blocare")),
                ("rating_sum", models.IntegerField(default=0, verbose_name="Sumă stele (user→transportator)")),
                ("rating_count", models.PositiveIntegerField(default=0, verbose_name="Număr evaluări (user→transportator)")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transport_operator_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Profil transportator",
                "verbose_name_plural": "Profile transportatori",
            },
        ),
    ]
