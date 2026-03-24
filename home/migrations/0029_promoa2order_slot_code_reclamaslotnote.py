from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0028_rename_home_collab_partner_7a8b2c_idx_home_collab_partner_9435f3_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="promoa2order",
            name="slot_code",
            field=models.CharField(db_index=True, default="A2", max_length=20, verbose_name="Caseta promovare"),
        ),
        migrations.CreateModel(
            name="ReclamaSlotNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("section", models.CharField(db_index=True, max_length=30, verbose_name="Secțiune")),
                ("slot_code", models.CharField(db_index=True, max_length=30, verbose_name="Slot")),
                ("text", models.TextField(blank=True, default="", verbose_name="Text notiță")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Actualizat la")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Creat la")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reclama_slot_notes_updated", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Notiță slot Reclama",
                "verbose_name_plural": "Notițe sloturi Reclama",
                "ordering": ["section", "slot_code"],
                "unique_together": {("section", "slot_code")},
            },
        ),
    ]
