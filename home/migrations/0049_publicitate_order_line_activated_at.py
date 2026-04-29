from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0048_publicitate_order_line_schedule_and_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="publicitateorderline",
            name="activated_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Activat la"),
        ),
    ]
