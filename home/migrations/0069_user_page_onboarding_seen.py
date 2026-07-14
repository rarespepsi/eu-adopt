# Generated manually for user onboarding seen pages

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0068_site_login_event"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserPageOnboardingSeen",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("page_key", models.CharField(db_index=True, max_length=64, verbose_name="Pagină")),
                ("seen_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="onboarding_pages_seen",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Onboarding pagină văzut",
                "verbose_name_plural": "Onboarding pagini văzute",
            },
        ),
        migrations.AddIndex(
            model_name="userpageonboardingseen",
            index=models.Index(fields=["user", "page_key"], name="home_userpa_user_id_6f2a1c_idx"),
        ),
        migrations.AddConstraint(
            model_name="userpageonboardingseen",
            constraint=models.UniqueConstraint(fields=("user", "page_key"), name="uniq_user_onboard_page"),
        ),
    ]
