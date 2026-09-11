# Generated manually — FacebookOutboundPost kind pierdut/găsit

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0090_userprofile_weekly_thanks_sent_at"),
    ]

    operations = [
        migrations.AlterField(
            model_name="facebookoutboundpost",
            name="kind",
            field=models.CharField(
                choices=[
                    ("animal", "Animal"),
                    ("campanie", "Campanie sterilizare"),
                    ("pierdut", "Pierdut / găsit"),
                    ("ro_mirror", "Mirror postare RO"),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
    ]
