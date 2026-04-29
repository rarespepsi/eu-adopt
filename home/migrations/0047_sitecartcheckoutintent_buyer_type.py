from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0046_sitecartcheckoutintent"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitecartcheckoutintent",
            name="buyer_type",
            field=models.CharField(
                choices=[("pf", "Persoană fizică"), ("pj", "Persoană juridică")],
                default="pf",
                max_length=8,
                verbose_name="Tip cumpărător",
            ),
        ),
    ]
