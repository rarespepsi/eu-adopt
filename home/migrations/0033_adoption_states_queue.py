from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0032_contactmessage_attachment"),
    ]

    operations = [
        migrations.AddField(
            model_name="animallisting",
            name="adoption_state",
            field=models.CharField(
                choices=[
                    ("liber", "Liber"),
                    ("spre_adoptie", "Spre adopție"),
                    ("in_curs_adoptie", "În curs de adopție"),
                    ("adoptat", "Adoptat"),
                ],
                db_index=True,
                default="liber",
                max_length=20,
                verbose_name="Stare adopție",
            ),
        ),
        migrations.AddField(
            model_name="adoptionrequest",
            name="accepted_expires_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Acceptare valabilă până la"),
        ),
        migrations.AddField(
            model_name="adoptionrequest",
            name="extension_count",
            field=models.PositiveSmallIntegerField(default=0, verbose_name="Număr prelungiri"),
        ),
        migrations.AlterField(
            model_name="adoptionrequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("in_asteptare", "În așteptare (owner)"),
                    ("acceptata", "Acceptată"),
                    ("respinsa", "Respinsă"),
                    ("expirata_neconfirmata", "Expirată neconfirmată"),
                    ("finalizata", "Adopție finalizată"),
                ],
                default="in_asteptare",
                max_length=32,
                verbose_name="Stare",
            ),
        ),
    ]
