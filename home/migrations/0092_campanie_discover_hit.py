# Generated manually for CampanieDiscoverHit

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0091_facebook_outbound_kind_pierdut"),
    ]

    operations = [
        migrations.CreateModel(
            name="CampanieDiscoverHit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("url", models.URLField(max_length=500, unique=True)),
                ("url_norm", models.CharField(blank=True, db_index=True, default="", max_length=500)),
                ("judet", models.CharField(db_index=True, max_length=64)),
                ("judet_slug", models.CharField(db_index=True, max_length=80)),
                ("judet_code", models.CharField(blank=True, default="", max_length=8)),
                ("title", models.CharField(blank=True, default="", max_length=300)),
                ("snippet", models.CharField(blank=True, default="", max_length=500)),
                ("image_url", models.URLField(blank=True, default="", max_length=500)),
                ("guessed_dates", models.CharField(blank=True, default="", max_length=120)),
                ("source", models.CharField(blank=True, default="", max_length=16)),
                ("query", models.CharField(blank=True, default="", max_length=240)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "Nou"),
                            ("skipped", "Omis"),
                            ("published", "Publicat"),
                            ("quarantine", "Carantină / vechi"),
                        ],
                        db_index=True,
                        default="new",
                        max_length=16,
                    ),
                ),
                ("skip_reason", models.CharField(blank=True, default="", max_length=240)),
                ("localitate_guess", models.CharField(blank=True, default="", max_length=120)),
                ("date_start", models.DateField(blank=True, null=True)),
                ("date_end", models.DateField(blank=True, null=True)),
                ("first_seen_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                (
                    "campanie",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="discover_hits",
                        to="home.campaniesterilizare",
                    ),
                ),
            ],
            options={
                "verbose_name": "Descoperire campanie",
                "verbose_name_plural": "Descoperiri campanii",
                "ordering": ["-last_seen_at", "-pk"],
            },
        ),
        migrations.AddIndex(
            model_name="campaniediscoverhit",
            index=models.Index(fields=["status", "judet_slug"], name="home_campan_status_7a1b2c_idx"),
        ),
        migrations.AddIndex(
            model_name="campaniediscoverhit",
            index=models.Index(fields=["last_seen_at"], name="home_campan_last_se_8d3e4f_idx"),
        ),
    ]
