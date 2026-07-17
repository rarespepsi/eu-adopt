from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0072_alter_animallisting_cip_rua_max24"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="despre_noi",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Opțional, max. ~2–3 rânduri pe pagina publică Adăpost/ONG.",
                max_length=280,
                verbose_name="Despre noi (pagină adăpost)",
            ),
        ),
    ]
