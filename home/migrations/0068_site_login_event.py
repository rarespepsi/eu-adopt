# Generated for T₀ login metrics

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0067_site_presence"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteLoginEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("logged_in_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("login", "Login Intra"),
                            ("signup_verify_email", "Activare email signup"),
                            ("signup_complete_login", "Login one-time după activare"),
                        ],
                        db_index=True,
                        default="login",
                        max_length=32,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="site_login_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Eveniment login",
                "verbose_name_plural": "Evenimente login",
                "ordering": ["-logged_in_at"],
            },
        ),
        migrations.AddIndex(
            model_name="siteloginevent",
            index=models.Index(fields=["logged_in_at", "user"], name="home_sitelo_logged__a1b2c3_idx"),
        ),
        migrations.AddIndex(
            model_name="siteloginevent",
            index=models.Index(fields=["user", "logged_in_at"], name="home_sitelo_user_id_d4e5f6_idx"),
        ),
    ]
