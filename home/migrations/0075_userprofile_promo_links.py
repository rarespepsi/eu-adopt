from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0074_userprofile_link_extern_despre_noi_360"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="link_social",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Slot 1 pe pagina publică adăpost.",
                max_length=500,
                verbose_name="Link social (FB / Insta / TikTok)",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="link_mancare",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Slot 2 pe pagina publică adăpost.",
                max_length=500,
                verbose_name="Link mâncare adăpost",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="link_propriu",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Slot 3 pe pagina publică; gol = Suflet și Caracter.",
                max_length=500,
                verbose_name="Link propriu / reclamă",
            ),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="link_extern",
            field=models.CharField(
                blank=True,
                default="",
                help_text="URL opțional (site, Facebook, etc.) — Cont DATE FIRMĂ + Despre noi public.",
                max_length=500,
                verbose_name="Link site / pagină",
            ),
        ),
    ]
