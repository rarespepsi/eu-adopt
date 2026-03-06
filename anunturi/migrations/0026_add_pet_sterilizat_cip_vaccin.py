# Generated manually for EU-Adopt

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anunturi', '0025_add_pet_imagine_2_imagine_3'),
    ]

    operations = [
        migrations.AddField(
            model_name='pet',
            name='sterilizat',
            field=models.BooleanField(blank=True, null=True, verbose_name='Sterilizat/Castrat'),
        ),
        migrations.AddField(
            model_name='pet',
            name='cip',
            field=models.CharField(blank=True, max_length=50, verbose_name='Număr CIP'),
        ),
        migrations.AddField(
            model_name='pet',
            name='vaccin',
            field=models.CharField(blank=True, max_length=200, verbose_name='Vaccin (da/nu/detalii)'),
        ),
    ]
