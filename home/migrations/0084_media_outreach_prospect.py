# Generated manually — doar MediaOutreachProspect (fără rename indexuri stray).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0083_staffonboardinglead_uat_category"),
    ]

    operations = [
        migrations.CreateModel(
            name="MediaOutreachProspect",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "media_kind",
                    models.CharField(
                        choices=[
                            ("radio", "Radio"),
                            ("tv", "TV"),
                            ("press", "Ziar / redacție"),
                            ("podcast", "Podcast"),
                            ("other", "Altele"),
                        ],
                        db_index=True,
                        default="press",
                        max_length=16,
                        verbose_name="Tip media",
                    ),
                ),
                (
                    "outlet_name",
                    models.CharField(db_index=True, max_length=255, verbose_name="Denumire (post / redacție)"),
                ),
                (
                    "contact_name",
                    models.CharField(blank=True, default="", max_length=200, verbose_name="Persoană contact"),
                ),
                (
                    "email",
                    models.EmailField(blank=True, db_index=True, default="", max_length=254, verbose_name="E-mail"),
                ),
                ("phone", models.CharField(blank=True, default="", max_length=40, verbose_name="Telefon")),
                ("website", models.CharField(blank=True, default="", max_length=500, verbose_name="Site / URL")),
                (
                    "judet",
                    models.CharField(blank=True, db_index=True, default="", max_length=120, verbose_name="Județ"),
                ),
                ("oras", models.CharField(blank=True, default="", max_length=120, verbose_name="Oraș")),
                ("notes", models.TextField(blank=True, default="", verbose_name="Note")),
                (
                    "source",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="ex. web, import CSV, manual",
                        max_length=120,
                        verbose_name="Sursă date",
                    ),
                ),
                (
                    "outreach_status",
                    models.CharField(
                        choices=[
                            ("new", "Nou"),
                            ("emailed", "Email trimis"),
                            ("wa_ready", "Text WA pregătit"),
                            ("contacted", "Contactat"),
                            ("replied", "A răspuns"),
                            ("partner", "Partener"),
                            ("do_not_contact", "Nu contacta"),
                        ],
                        db_index=True,
                        default="new",
                        max_length=20,
                        verbose_name="Status outreach",
                    ),
                ),
                ("last_email_sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Prospect media (Audio/TV)",
                "verbose_name_plural": "Prospecte media (Audio/TV)",
                "ordering": ["media_kind", "judet", "outlet_name"],
            },
        ),
        migrations.AddIndex(
            model_name="mediaoutreachprospect",
            index=models.Index(fields=["media_kind", "outreach_status"], name="home_mediao_media_k_4f7422_idx"),
        ),
        migrations.AddIndex(
            model_name="mediaoutreachprospect",
            index=models.Index(fields=["-updated_at"], name="home_mediao_updated_ebdf82_idx"),
        ),
    ]
