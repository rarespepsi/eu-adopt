"""
Date beneficiar / ONG pentru documente donații (hardcodate până la configurare dinamică).
"""

EUADOPT_DONATION_ORG = {
    "name": "EU-ADOPT (operator platformă — denumire legală în curs)",
    "cui": "— în curs de completare —",
    "address": "— sediu în curs de completare —",
    "iban": "RO00BANK0000000000000000",
    "bank": "— bancă în curs —",
    "email_contact": "euadopt@gmail.com",
}

# Benzi cursivă PT (P1/P3) și Servicii (S1/S7): celula EU *.2 → pagina Donații, secțiune SMS
EUADOPT_DONATION_SMS_PAGE_ANCHOR = "donatii-sms"
EUADOPT_SMS_STRIP_LABEL = "SMS"
EUADOPT_SMS_STRIP_MSG = (
    "Donație SMS: pași, completare și sisteme — vezi la pagina Donații."
)

# Benzi cursivă: celula EU *.3 — anunț app mobil (desk + mobil)
EUADOPT_PWA_STRIP_LABEL = "APP"
EUADOPT_PWA_STRIP_MSG = "App EU-Adopt pe MOBIL"

# Partener cauză animale — pagina Donații (date complete / IBAN partener la activare)
EUADOPT_PARTNER_NGO = {
    "name": "Suflet și Caracter",
    "legal_name": "Asociație pentru protecția animalelor",
    "badge": "Cont donații partener — activare în curs (final de lună)",
    "blurb": (
        "Asociația Suflet și Caracter este partenerul real desemnat pentru cauzele animalelor "
        "pe această pagină. IBAN-ul și datele complete pentru donații direct către asociație "
        "vor fi afișate după activarea finală."
    ),
}
