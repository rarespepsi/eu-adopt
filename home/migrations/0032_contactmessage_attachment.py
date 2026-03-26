from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0031_contactmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="contactmessage",
            name="attachment",
            field=models.FileField(blank=True, null=True, upload_to="contact_attachments/", verbose_name="Fișier atașat"),
        ),
    ]
