from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0081_facebook_multi_market"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="phone_landline",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Opțional. Prefix zonă + număr (fără SMS).",
                max_length=40,
                verbose_name="Telefon fix / sediu",
            ),
        ),
    ]
