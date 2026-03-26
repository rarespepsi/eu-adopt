from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0029_promoa2order_slot_code_reclamaslotnote"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserLegalConsent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("consent_type", models.CharField(choices=[("terms", "Termeni și condiții"), ("privacy", "Politica de confidențialitate"), ("marketing", "Marketing / noutăți")], max_length=20, verbose_name="Tip consimțământ")),
                ("accepted", models.BooleanField(default=False, verbose_name="Acceptat")),
                ("version", models.CharField(default="1.0", max_length=20, verbose_name="Versiune document")),
                ("source", models.CharField(blank=True, default="", max_length=50, verbose_name="Sursă acțiune")),
                ("ip_address", models.CharField(blank=True, default="", max_length=64, verbose_name="IP")),
                ("user_agent", models.CharField(blank=True, default="", max_length=500, verbose_name="User-Agent")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Înregistrat la")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="legal_consents", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Consimțământ legal utilizator",
                "verbose_name_plural": "Consimțăminte legale utilizatori",
            },
        ),
        migrations.AddIndex(
            model_name="userlegalconsent",
            index=models.Index(fields=["user", "consent_type", "created_at"], name="home_userle_user_id_3965d4_idx"),
        ),
        migrations.AddIndex(
            model_name="userlegalconsent",
            index=models.Index(fields=["created_at"], name="home_userle_created_8da102_idx"),
        ),
    ]
