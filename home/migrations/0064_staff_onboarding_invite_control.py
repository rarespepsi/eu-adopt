# Generated manually — Faza A control invitații Add USER

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def _backfill_invite_status(apps, schema_editor):
    Lead = apps.get_model("home", "StaffOnboardingLead")
    Lead.objects.filter(invite_email_last_sent_at__isnull=False).update(invite_mail_status="sent")
    Lead.objects.filter(imported_user__isnull=False).update(invite_mail_status="signed_up")


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0063_partner_locations"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="staffonboardinglead",
            name="invite_mail_status",
            field=models.CharField(
                choices=[
                    ("never", "Niciodată trimis"),
                    ("sent", "Invitație trimisă"),
                    ("replied", "A răspuns"),
                    ("signed_up", "Cont creat"),
                    ("bounced", "Email returnat"),
                    ("opt_out", "Refuz contact"),
                    ("do_not_contact", "Nu contacta"),
                ],
                db_index=True,
                default="never",
                max_length=20,
                verbose_name="Stare mail invitație",
            ),
        ),
        migrations.AddField(
            model_name="staffonboardinglead",
            name="invite_replied_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Răspuns la invitație"),
        ),
        migrations.AddField(
            model_name="staffonboardinglead",
            name="invite_max_sends",
            field=models.PositiveSmallIntegerField(
                default=3,
                help_text="După acest număr nu se mai trimite (doar trimiteri reale, nu simulări).",
                verbose_name="Max. trimiteri invitație",
            ),
        ),
        migrations.AddField(
            model_name="staffonboardinglead",
            name="invite_cooldown_days",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Gol = folosește setarea globală (implicit 14 zile).",
                null=True,
                verbose_name="Cooldown retrimitere (zile)",
            ),
        ),
        migrations.AddField(
            model_name="staffonboardinglead",
            name="invite_staff_notes",
            field=models.TextField(blank=True, default="", verbose_name="Notițe invitație email"),
        ),
        migrations.CreateModel(
            name="StaffOnboardingInviteLog",
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
                    "lead",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="invite_logs",
                        to="home.staffonboardinglead",
                    ),
                ),
                (
                    "sent_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="staff_onboarding_invite_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Log invitație lead",
                "verbose_name_plural": "Loguri invitații lead",
                "ordering": ["-sent_at"],
                "indexes": [models.Index(fields=["lead", "-sent_at"], name="home_staff_inv_lead_sent")],
            },
        ),
        migrations.RunPython(_backfill_invite_status, migrations.RunPython.noop),
    ]
