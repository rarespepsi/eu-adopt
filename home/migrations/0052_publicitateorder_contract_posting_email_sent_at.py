# Generated manually for publicitate contract/posting summary email idempotency.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0051_promo_a2_slot_plans"),
    ]

    operations = [
        migrations.AddField(
            model_name="publicitateorder",
            name="contract_posting_email_sent_at",
            field=models.DateTimeField(
                blank=True,
                help_text="După plată: e-mail cu rezumat sloturi/perioade/coduri (idempotent).",
                null=True,
                verbose_name="Email detalii postare trimis la",
            ),
        ),
    ]
