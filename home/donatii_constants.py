"""
Date beneficiar / operator / partener pentru documente donații și pagini legale.
"""

# Operator platformă (SRL) — obligatoriu pe Termeni, Contact, GDPR (Legea 365/2002, GDPR).
EUADOPT_PLATFORM_OPERATOR = {
    "legal_name": "Animal Connect SRL",
    "brand": "EU-ADOPT",
    "cui": "45764253",
    "reg_com": "J27/294/2022",
    "address": "Str. Plantelor nr. 19K, ap. 1, Piatra Neamț, jud. Neamț",
    "email": "contact@eu-adopt.ro",
}

EUADOPT_LEGAL_DETAILS_NOTE = (
    "IBAN-ul partenerului pentru donații și alte detalii bancare — la cerere, "
    "la contact@eu-adopt.ro (cont bancar în curs de deschidere)."
)

# Partener cauză animale / beneficiar donații (asociație).
EUADOPT_PARTNER_NGO = {
    "name": "Suflet și Caracter",
    "legal_name": "Asociația Suflet și Caracter",
    "cui": "42080757",
    "address": "Strada Bistriței nr. 10, Bl. F24, Piatra Neamț, jud. Neamț",
    "locality": "Piatra Neamț",
    "county": "Neamț",
    "location_display": "Piatra Neamț, jud. Neamț",
    # Aceeași persoană / canale de contact ca operatorul platformei.
    "email": EUADOPT_PLATFORM_OPERATOR["email"],
    "badge": "Partener cauză animale",
    "blurb": (
        "Asociația Suflet și Caracter este partenerul desemnat pentru cauzele animale "
        "pe această platformă. Pe site publicăm denumirea, CUI/CIF și sediul; "
        "IBAN-ul bancar — la cerere, după deschiderea contului (contact@eu-adopt.ro)."
    ),
    "url": "https://eu-adopt.ro/donatii/",
}

# Beneficiar donații / PDF-uri (IBAN gol până la deschiderea contului la bancă).
EUADOPT_DONATION_ORG = {
    "name": EUADOPT_PARTNER_NGO["legal_name"],
    "cui": EUADOPT_PARTNER_NGO["cui"],
    "address": EUADOPT_PARTNER_NGO["address"],
    "iban": "",
    "bank": "",
    "email_contact": EUADOPT_PLATFORM_OPERATOR["email"],
}

# Benzi cursivă PT (P1/P3) și Servicii (S1/S7): celula EU *.2 → pagina Donații, secțiune SMS
EUADOPT_DONATION_SMS_PAGE_ANCHOR = "donatii-sms"
EUADOPT_SMS_STRIP_LABEL = "SMS"
EUADOPT_SMS_STRIP_MSG = (
    "Donație SMS: pași, completare și sisteme — vezi la pagina Donații."
)
EUADOPT_SMS_STRIP_MSG_EN = "SMS donation: steps and systems — see the Donations page."

# Benzi cursivă: celula EU *.3 — anunț app mobil (desk + mobil)
EUADOPT_PWA_STRIP_LABEL = "APP"
EUADOPT_PWA_STRIP_MSG = "App EU-Adopt pe MOBIL"
EUADOPT_PWA_STRIP_MSG_EN = "EU-Adopt app on MOBILE"
