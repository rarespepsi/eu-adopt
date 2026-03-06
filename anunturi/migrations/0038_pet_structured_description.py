# Descriere structurată: temperament, stil viață, compatibilitate, status medical, educație, recomandare, descriere_personalitate.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("anunturi", "0037_remove_tip_altele_altul_and_varsta"),
    ]

    operations = [
        # Temperament
        migrations.AddField(model_name="pet", name="prietenos_cu_oamenii", field=models.BooleanField(blank=True, default=False, verbose_name="Prietenos cu oamenii")),
        migrations.AddField(model_name="pet", name="prietenos_cu_copiii", field=models.BooleanField(blank=True, default=False, verbose_name="Prietenos cu copiii")),
        migrations.AddField(model_name="pet", name="timid", field=models.BooleanField(blank=True, default=False, verbose_name="Timid")),
        migrations.AddField(model_name="pet", name="protector", field=models.BooleanField(blank=True, default=False, verbose_name="Protector")),
        migrations.AddField(model_name="pet", name="energic_jucaus", field=models.BooleanField(blank=True, default=False, verbose_name="Energic, jucăuș")),
        migrations.AddField(model_name="pet", name="linistit", field=models.BooleanField(blank=True, default=False, verbose_name="Liniștit")),
        migrations.AddField(model_name="pet", name="independent", field=models.BooleanField(blank=True, default=False, verbose_name="Independent")),
        migrations.AddField(model_name="pet", name="cauta_atentie", field=models.BooleanField(blank=True, default=False, verbose_name="Caută atenție")),
        migrations.AddField(model_name="pet", name="latra_des", field=models.BooleanField(blank=True, default=False, verbose_name="Lată des")),
        migrations.AddField(model_name="pet", name="calm_in_casa", field=models.BooleanField(blank=True, default=False, verbose_name="Calm în casă")),
        # Stil de viață
        migrations.AddField(model_name="pet", name="potrivit_apartament", field=models.BooleanField(blank=True, default=False, verbose_name="Potrivit apartament")),
        migrations.AddField(model_name="pet", name="prefera_curte", field=models.BooleanField(blank=True, default=False, verbose_name="Preferă curte")),
        migrations.AddField(model_name="pet", name="poate_sta_afara", field=models.BooleanField(blank=True, default=False, verbose_name="Poate sta afară")),
        migrations.AddField(model_name="pet", name="poate_sta_interior", field=models.BooleanField(blank=True, default=False, verbose_name="Poate sta în interior")),
        migrations.AddField(model_name="pet", name="obisnuit_in_lesa", field=models.BooleanField(blank=True, default=False, verbose_name="Obisnuit în lesă")),
        migrations.AddField(model_name="pet", name="merge_bine_la_plimbare", field=models.BooleanField(blank=True, default=False, verbose_name="Merge bine la plimbare")),
        migrations.AddField(model_name="pet", name="necesita_miscare_multa", field=models.BooleanField(blank=True, default=False, verbose_name="Necesită mișcare multă")),
        migrations.AddField(model_name="pet", name="potrivit_persoane_varstnice", field=models.BooleanField(blank=True, default=False, verbose_name="Potrivit persoane vârstnice")),
        migrations.AddField(model_name="pet", name="potrivit_familie_activa", field=models.BooleanField(blank=True, default=False, verbose_name="Potrivit familie activă")),
        # Compatibilitate
        migrations.AddField(model_name="pet", name="ok_cu_alti_caini", field=models.BooleanField(blank=True, default=False, verbose_name="OK cu alți câini")),
        migrations.AddField(model_name="pet", name="ok_cu_pisici", field=models.BooleanField(blank=True, default=False, verbose_name="OK cu pisici")),
        migrations.AddField(model_name="pet", name="prefera_singurul_animal", field=models.BooleanField(blank=True, default=False, verbose_name="Preferă singurul animal")),
        migrations.AddField(model_name="pet", name="accepta_vizitatori", field=models.BooleanField(blank=True, default=False, verbose_name="Acceptă vizitatori")),
        migrations.AddField(model_name="pet", name="necesita_socializare", field=models.BooleanField(blank=True, default=False, verbose_name="Necesită socializare")),
        # Status medical
        migrations.AddField(model_name="pet", name="vaccinat", field=models.BooleanField(blank=True, default=False, verbose_name="Vaccinat")),
        migrations.AddField(model_name="pet", name="deparazitat", field=models.BooleanField(blank=True, default=False, verbose_name="Deparazitat")),
        migrations.AddField(model_name="pet", name="microcipat", field=models.BooleanField(blank=True, default=False, verbose_name="Microcipat")),
        migrations.AddField(model_name="pet", name="are_pasaport", field=models.BooleanField(blank=True, default=False, verbose_name="Are pașaport")),
        migrations.AddField(model_name="pet", name="necesita_tratament", field=models.BooleanField(blank=True, default=False, verbose_name="Necesită tratament")),
        migrations.AddField(model_name="pet", name="sensibil_zgomote", field=models.BooleanField(blank=True, default=False, verbose_name="Sensibil la zgomote")),
        # Educație
        migrations.AddField(model_name="pet", name="stie_comenzi_baza", field=models.BooleanField(blank=True, default=False, verbose_name="Știe comenzi de bază")),
        migrations.AddField(model_name="pet", name="face_nevoile_afara", field=models.BooleanField(blank=True, default=False, verbose_name="Face nevoile afară")),
        migrations.AddField(model_name="pet", name="invata_repede", field=models.BooleanField(blank=True, default=False, verbose_name="Învață repede")),
        migrations.AddField(model_name="pet", name="necesita_dresaj", field=models.BooleanField(blank=True, default=False, verbose_name="Necesită dresaj")),
        migrations.AddField(model_name="pet", name="nu_roade", field=models.BooleanField(blank=True, default=False, verbose_name="Nu roade")),
        migrations.AddField(model_name="pet", name="obisnuit_masina", field=models.BooleanField(blank=True, default=False, verbose_name="Obisnuit mașină")),
        # Recomandare specială
        migrations.AddField(model_name="pet", name="recomandat_prima_adoptie", field=models.BooleanField(blank=True, default=False, verbose_name="Recomandat pentru prima adopție")),
        # Descriere personalitate
        migrations.AddField(
            model_name="pet",
            name="descriere_personalitate",
            field=models.CharField(blank=True, help_text="Max 500 caractere. Completare liberă.", max_length=500, verbose_name="Descriere personalitate"),
        ),
    ]
