from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0073_userprofile_despre_noi"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="despre_noi",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Opțional, max. ~3–4 rânduri (Cont + pagina publică adăpost).",
                max_length=360,
                verbose_name="Despre noi",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="link_extern",
            field=models.CharField(
                blank=True,
                default="",
                help_text="URL opțional (site, Facebook, etc.) — valabil pentru toate tipurile de cont.",
                max_length=500,
                verbose_name="Link site / pagină",
            ),
        ),
    ]
