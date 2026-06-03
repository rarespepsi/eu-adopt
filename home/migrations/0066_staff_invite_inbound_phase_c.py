# Faza C — Message-ID pe log + inbound invitații

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0065_staffonboardinginvitelog_template_wave"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffonboardinginvitelog",
            name="message_id",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                max_length=255,
                verbose_name="Message-ID SMTP",
            ),
        ),
        migrations.CreateModel(
            name="StaffOnboardingInviteInbound",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("received_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("from_email", models.EmailField(blank=True, default="", max_length=254)),
                ("subject", models.CharField(blank=True, default="", max_length=255)),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("reply", "Răspuns"),
                            ("bounce", "Returnat / bounce"),
                            ("opt_out", "Nu contacta"),
                            ("unknown", "Necunoscut"),
                        ],
                        db_index=True,
                        max_length=12,
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[("imap", "IMAP inbox"), ("webhook", "Webhook")],
                        db_index=True,
                        max_length=12,
                    ),
                ),
                ("external_id", models.CharField(blank=True, db_index=True, default="", max_length=120)),
                ("snippet", models.TextField(blank=True, default="")),
                (
                    "lead",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="invite_inbounds",
                        to="home.staffonboardinglead",
                    ),
                ),
            ],
            options={
                "verbose_name": "Inbound invitație",
                "verbose_name_plural": "Inbound invitații",
                "ordering": ["-received_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="staffonboardinginviteinbound",
            constraint=models.UniqueConstraint(
                condition=models.Q(("external_id", ""), _negated=True),
                fields=("source", "external_id"),
                name="home_staff_inv_inbound_src_ext_uniq",
            ),
        ),
    ]
