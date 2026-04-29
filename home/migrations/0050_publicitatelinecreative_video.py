from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0049_publicitate_order_line_activated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="publicitatelinecreative",
            name="video",
            field=models.FileField(blank=True, null=True, upload_to="pub_creative/%Y/%m/", verbose_name="Video banner"),
        ),
    ]
