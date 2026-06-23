# Generated manually for site presence tracking

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("home", "0066_staff_invite_inbound_phase_c"),
    ]

    operations = [
        migrations.CreateModel(
            name="SitePresenceDaily",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField(db_index=True, unique=True)),
                ("page_views", models.PositiveIntegerField(default=0)),
                ("unique_visitors", models.PositiveIntegerField(default=0)),
                ("unique_logged_in", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Prezență site — zi",
                "verbose_name_plural": "Prezență site — zile",
                "ordering": ["-date"],
            },
        ),
        migrations.CreateModel(
            name="SitePresenceDaySession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("day", models.DateField(db_index=True)),
                ("session_hash", models.CharField(db_index=True, max_length=64)),
            ],
            options={
                "verbose_name": "Prezență sesiune zi",
                "verbose_name_plural": "Prezență sesiuni zilnice",
            },
        ),
        migrations.CreateModel(
            name="SitePresenceActive",
            fields=[
                ("session_hash", models.CharField(max_length=64, primary_key=True, serialize=False)),
                ("last_seen", models.DateTimeField(db_index=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="presence_active_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Sesiune activă",
                "verbose_name_plural": "Sesiuni active",
            },
        ),
        migrations.CreateModel(
            name="SitePresenceDayUser",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("day", models.DateField(db_index=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="presence_days",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Prezență user zi",
                "verbose_name_plural": "Prezență useri zilnic",
            },
        ),
        migrations.AddIndex(
            model_name="sitepresencedaysession",
            index=models.Index(fields=["day", "session_hash"], name="home_site_p_day_sess_idx"),
        ),
        migrations.AddIndex(
            model_name="sitepresenceactive",
            index=models.Index(fields=["-last_seen"], name="home_site_p_last_seen_idx"),
        ),
        migrations.AddIndex(
            model_name="sitepresenceactive",
            index=models.Index(fields=["last_seen", "user"], name="home_site_p_seen_user_idx"),
        ),
        migrations.AddConstraint(
            model_name="sitepresencedaysession",
            constraint=models.UniqueConstraint(
                fields=("day", "session_hash"),
                name="home_site_presence_day_sess_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="sitepresencedayuser",
            constraint=models.UniqueConstraint(
                fields=("day", "user"),
                name="home_site_presence_day_user_uniq",
            ),
        ),
    ]
