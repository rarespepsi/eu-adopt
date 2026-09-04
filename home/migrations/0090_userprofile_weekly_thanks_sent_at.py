# Generated manually for weekly new-member thanks email

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0089_abuse_report_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="weekly_thanks_sent_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                help_text="O singură dată: mulțumire + îndemn recomandare colaboratori.",
                null=True,
                verbose_name="Mail mulțumire săptămânal (membri noi) trimis la",
            ),
        ),
    ]
