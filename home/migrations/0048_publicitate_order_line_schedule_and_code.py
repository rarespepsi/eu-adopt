from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0047_sitecartcheckoutintent_buyer_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="publicitateorderline",
            name="ends_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="Data finalizare"),
        ),
        migrations.AddField(
            model_name="publicitateorderline",
            name="reactivation_count",
            field=models.PositiveSmallIntegerField(default=0, verbose_name="Număr reactivări"),
        ),
        migrations.AddField(
            model_name="publicitateorderline",
            name="starts_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="Data începere"),
        ),
        migrations.AddField(
            model_name="publicitateorderline",
            name="validation_code",
            field=models.CharField(blank=True, db_index=True, default="", max_length=16, verbose_name="Cod validare casetă"),
        ),
    ]
