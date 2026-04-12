# Generated manually for unified inbox notifications

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("home", "0040_site_cart_item"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserInboxNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(db_index=True, max_length=64, verbose_name="Tip")),
                ("title", models.CharField(max_length=200, verbose_name="Titlu")),
                ("body", models.TextField(blank=True, default="", max_length=4000, verbose_name="Text")),
                ("link_url", models.CharField(blank=True, default="", max_length=500, verbose_name="Link")),
                ("metadata", models.JSONField(blank=True, default=dict, verbose_name="Meta")),
                ("is_read", models.BooleanField(db_index=True, default=False, verbose_name="Citit")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creat la")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inbox_notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Notificare inbox utilizator",
                "verbose_name_plural": "Notificări inbox utilizatori",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="userinboxnotification",
            index=models.Index(fields=["user", "is_read", "created_at"], name="home_userin_user_id_7a1b2c_idx"),
        ),
        migrations.AddIndex(
            model_name="userinboxnotification",
            index=models.Index(fields=["user", "created_at"], name="home_userin_user_id_8d3e4f_idx"),
        ),
    ]
