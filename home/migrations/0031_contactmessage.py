from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0030_userlegalconsent"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContactMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("full_name", models.CharField(max_length=120, verbose_name="Nume")),
                ("email", models.EmailField(max_length=254, verbose_name="E-mail")),
                ("phone", models.CharField(blank=True, default="", max_length=40, verbose_name="Telefon")),
                ("topic", models.CharField(choices=[("general", "Suport general"), ("gdpr", "Date personale (GDPR)"), ("commercial", "Publicitate / servicii plătite"), ("moderation", "Moderare / raportări")], default="general", max_length=20, verbose_name="Tip solicitare")),
                ("subject", models.CharField(max_length=180, verbose_name="Subiect")),
                ("message", models.TextField(max_length=3000, verbose_name="Mesaj")),
                ("accepted_privacy", models.BooleanField(default=False, verbose_name="Acord confidențialitate")),
                ("ip_address", models.CharField(blank=True, default="", max_length=64, verbose_name="IP")),
                ("user_agent", models.CharField(blank=True, default="", max_length=500, verbose_name="User-Agent")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Trimis la")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="contact_messages", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Mesaj Contact",
                "verbose_name_plural": "Mesaje Contact",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="contactmessage",
            index=models.Index(fields=["topic", "created_at"], name="home_contac_topic_5b60f6_idx"),
        ),
        migrations.AddIndex(
            model_name="contactmessage",
            index=models.Index(fields=["email", "created_at"], name="home_contac_email_651ac3_idx"),
        ),
    ]
