from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0082_userprofile_phone_landline"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffonboardinglead",
            name="uat_category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "—"),
                    ("cj", "CJ"),
                    ("pmb", "PMB"),
                    ("primarie_municipiu", "Primărie municipiu"),
                    ("primarie_oras", "Primărie oraș"),
                    ("primarie_comuna", "Primărie comună"),
                ],
                db_index=True,
                default="",
                help_text="Consiliu județean / PMB / primărie (municipiu, oraș, comună). Gol = nu e prospect UAT.",
                max_length=24,
                verbose_name="Categorie UAT",
            ),
        ),
    ]
