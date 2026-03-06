# Generated manually – adăpost public + carnet sănătate

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anunturi', '0026_add_pet_sterilizat_cip_vaccin'),
    ]

    operations = [
        migrations.AddField(
            model_name='pet',
            name='adapost_public',
            field=models.BooleanField(
                default=False,
                help_text='Bifat doar pentru adăposturi publice. Pentru adăpost public, sterilizat, CIP și carnet sănătate sunt obligatorii. Persoane fizice și ONG/asociații nu bifează.',
                verbose_name='Adăpost public',
            ),
        ),
        migrations.AddField(
            model_name='pet',
            name='carnet_sanatate',
            field=models.CharField(
                blank=True,
                help_text='Obligatoriu pentru adăposturi publice.',
                max_length=200,
                verbose_name='Carnet de sănătate',
            ),
        ),
    ]
