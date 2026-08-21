import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0084_media_outreach_prospect"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="mediaoutreachprospect",
            name="cooldown_days",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Gol = setare globală (implicit 7 zile).",
                null=True,
                verbose_name="Cooldown retrimitere (zile)",
            ),
        ),
        migrations.AddField(
            model_name="mediaoutreachprospect",
            name="max_sends",
            field=models.PositiveSmallIntegerField(
                default=3,
                help_text="După acest număr nu se mai trimite (doar trimiteri reale).",
                verbose_name="Max. trimiteri email",
            ),
        ),
        migrations.AddField(
            model_name="mediaoutreachprospect",
            name="replied_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Răspuns redacție"),
        ),
        migrations.AlterField(
            model_name="mediaoutreachprospect",
            name="last_email_sent_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Ultimul email outreach"),
        ),
        migrations.CreateModel(
            name="MediaOutreachInviteLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sent_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("to_email", models.EmailField(max_length=254)),
                ("subject", models.CharField(blank=True, default="", max_length=255)),
                (
                    "outcome",
                    models.CharField(
                        choices=[
                            ("sent", "Trimis"),
                            ("error", "Eroare SMTP"),
                            ("dry_run", "Simulare (mail dezactivat)"),
                        ],
                        db_index=True,
                        max_length=12,
                    ),
                ),
                ("error_message", models.TextField(blank=True, default="")),
                (
                    "dispatch_kind",
                    models.CharField(
                        choices=[("manual", "Bifă manuală"), ("wave", "Val")],
                        db_index=True,
                        default="manual",
                        max_length=10,
                    ),
                ),
                ("message_id", models.CharField(blank=True, default="", max_length=255)),
                (
                    "prospect",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="invite_logs",
                        to="home.mediaoutreachprospect",
                    ),
                ),
                (
                    "sent_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="media_outreach_invite_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Log email media outreach",
                "verbose_name_plural": "Loguri email media outreach",
                "ordering": ["-sent_at"],
            },
        ),
        migrations.AddIndex(
            model_name="mediaoutreachinvitelog",
            index=models.Index(fields=["prospect", "outcome", "sent_at"], name="home_mediao_prospec_e677ad_idx"),
        ),
    ]
