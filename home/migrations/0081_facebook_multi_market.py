# Generated manually — multi-market Facebook deliveries + RO inbound mirror

from django.db import migrations, models
import django.db.models.deletion


def forwards_seed_ro_deliveries(apps, schema_editor):
    Outbound = apps.get_model("home", "FacebookOutboundPost")
    Delivery = apps.get_model("home", "FacebookOutboundDelivery")
    for row in Outbound.objects.all().iterator():
        Delivery.objects.get_or_create(
            outbound_id=row.pk,
            market="ro",
            defaults={
                "status": row.status if row.status in ("pending", "posted", "failed", "skipped") else "pending",
                "facebook_post_id": row.facebook_post_id or "",
                "error": (row.error or "")[:500],
                "posted_at": row.posted_at,
                "attempt_count": 1 if row.status == "posted" else 0,
            },
        )


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0080_facebook_outbound_post"),
    ]

    operations = [
        migrations.AlterField(
            model_name="facebookoutboundpost",
            name="kind",
            field=models.CharField(
                choices=[
                    ("animal", "Animal"),
                    ("campanie", "Campanie sterilizare"),
                    ("ro_mirror", "Mirror postare RO"),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="facebookoutboundpost",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "În așteptare"),
                    ("posted", "Postat (toate piețele)"),
                    ("partial", "Parțial"),
                    ("failed", "Eșuat"),
                    ("skipped", "Omis"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AlterModelOptions(
            name="facebookoutboundpost",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Postare Facebook (sursă)",
                "verbose_name_plural": "Postări Facebook (surse)",
            },
        ),
        migrations.CreateModel(
            name="FacebookOutboundDelivery",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "market",
                    models.CharField(
                        choices=[
                            ("ro", "România"),
                            ("de", "Germania"),
                            ("fr", "Franța"),
                            ("es", "Spania"),
                            ("com", "International"),
                        ],
                        db_index=True,
                        max_length=8,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "În așteptare"),
                            ("posted", "Postat"),
                            ("failed", "Eșuat"),
                            ("skipped", "Omis"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("facebook_post_id", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("error", models.CharField(blank=True, default="", max_length=500)),
                ("attempt_count", models.PositiveSmallIntegerField(default=0)),
                ("posted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "outbound",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deliveries",
                        to="home.facebookoutboundpost",
                    ),
                ),
            ],
            options={
                "verbose_name": "Livrare Facebook",
                "verbose_name_plural": "Livrări Facebook",
                "ordering": ["outbound_id", "market"],
            },
        ),
        migrations.CreateModel(
            name="FacebookRoInboundPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_fb_post_id", models.CharField(db_index=True, max_length=64, unique=True)),
                ("message", models.TextField(blank=True, default="")),
                ("permalink", models.CharField(blank=True, default="", max_length=500)),
                ("picture_url", models.CharField(blank=True, default="", max_length=1000)),
                ("fb_created_time", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "În așteptare"),
                            ("processed", "Procesat (mirror)"),
                            ("skipped_auto", "Omis (auto site)"),
                            ("failed", "Eșuat"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("skip_reason", models.CharField(blank=True, default="", max_length=200)),
                ("error", models.CharField(blank=True, default="", max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "outbound",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ro_inbounds",
                        to="home.facebookoutboundpost",
                    ),
                ),
            ],
            options={
                "verbose_name": "Postare inbound Facebook RO",
                "verbose_name_plural": "Postări inbound Facebook RO",
                "ordering": ["-fb_created_time", "-pk"],
            },
        ),
        migrations.AddIndex(
            model_name="facebookoutbounddelivery",
            index=models.Index(fields=["status", "market", "created_at"], name="home_fb_del_status_mkt_idx"),
        ),
        migrations.AddIndex(
            model_name="facebookoutbounddelivery",
            index=models.Index(fields=["facebook_post_id"], name="home_fb_del_fbpost_idx"),
        ),
        migrations.AddConstraint(
            model_name="facebookoutbounddelivery",
            constraint=models.UniqueConstraint(
                fields=("outbound", "market"),
                name="uniq_fb_delivery_outbound_market",
            ),
        ),
        migrations.AddIndex(
            model_name="facebookroinboundpost",
            index=models.Index(fields=["status", "created_at"], name="home_fb_ro_in_status_idx"),
        ),
        migrations.RunPython(forwards_seed_ro_deliveries, backwards_noop),
    ]
