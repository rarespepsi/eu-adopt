from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0013_animallisting_observatii"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PetMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField(max_length=2000, verbose_name="Mesaj")),
                ("is_read", models.BooleanField(default=False, verbose_name="Citit")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creat la")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizat la")),
                ("animal", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="home.animallisting")),
                ("receiver", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pet_messages_received", to=settings.AUTH_USER_MODEL)),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pet_messages_sent", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Mesaj pet",
                "verbose_name_plural": "Mesaje pet",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["animal", "created_at"], name="pm_animal_created_idx"),
                    models.Index(fields=["receiver", "is_read", "created_at"], name="pm_recv_read_created_idx"),
                    models.Index(fields=["sender", "created_at"], name="pm_sender_created_idx"),
                ],
            },
        ),
    ]
