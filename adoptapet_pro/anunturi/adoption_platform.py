"""
Validare automată a platformei pentru cereri de adopție și trimitere email către ONG.

Verificarea de către noi se face prin condiții clare pe câmpuri/formular.
Emailul către ONG conține un link; la activare se trimit automat către ONG datele
adoptatorului și către adoptator datele de contact ONG.
"""
import re
import secrets
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse


# —— Condiții pentru validarea automată a platformei ——
# Toate trebuie îndeplinite ca cererea să fie aprobată automat și trimisă la ONG.

def _nume_complet_ok(value):
    """Nume complet: minim 2 cuvinte (nume + prenume), fără caractere suspecte."""
    if not value or not value.strip():
        return False
    s = value.strip()
    if len(s) < 4:
        return False
    words = [w for w in s.split() if len(w) >= 2]
    if len(words) < 2:
        return False
    return True


def _telefon_ok(value):
    """Telefon: conține cel puțin 10 cifre (format românesc)."""
    if not value:
        return False
    digits = re.sub(r"\D", "", value)
    return len(digits) >= 10


def _mesaj_ok(value):
    """Mesaj opțional: dacă e completat, lungime rezonabilă (max 2000 caractere)."""
    if not value or not value.strip():
        return True
    return len(value.strip()) <= 2000


def _adresa_ok(value):
    """Adresă opțională: dacă e completată, max 300 caractere (conform modelului)."""
    if not value or not value.strip():
        return True
    return len(value.strip()) <= 300


def platform_validation_passes(adoption_request):
    """
    Verifică dacă cererea de adopție îndeplinește toate condițiile de validare a platformei.
    Returnează True doar dacă toate condițiile sunt îndeplinite.
    """
    if not adoption_request:
        return False
    checks = [
        _nume_complet_ok(adoption_request.nume_complet),
        _telefon_ok(adoption_request.telefon),
        _mesaj_ok(adoption_request.mesaj),
        _adresa_ok(adoption_request.adresa),
    ]
    return all(checks)


def _validation_link(adoption_request, request=None):
    """Construiește URL-ul absolut pentru linkul de validare."""
    if not adoption_request.validation_token:
        return ""
    path = reverse("adoption_validate_token", kwargs={"token": adoption_request.validation_token})
    if request:
        return request.build_absolute_uri(path)
    base = getattr(settings, "SITE_URL", "").rstrip("/") or "https://adoptapet.ro"
    return f"{base}{path}"


def send_adoption_request_to_ong(adoption_request, request=None):
    """
    Trimite email către ONG (pet.ong_email) cu un link de validare (fără date adoptator în email).
    La activarea linkului se trimit datele adoptatorului către ONG și datele ONG către adoptator.
    Marchează cererea ca approved_platform. Returnează True dacă emailul a fost trimis.
    """
    pet = adoption_request.pet
    if not pet or not getattr(pet, "ong_email", None) or not pet.ong_email.strip():
        return False
    if not adoption_request.validation_token:
        adoption_request.validation_token = secrets.token_urlsafe(32)
        adoption_request.save(update_fields=["validation_token"])
    link = _validation_link(adoption_request, request)
    subject = f"[Adopt a Pet] Cerere adopție pentru {pet.nume} – validare"
    body = f"""Bună ziua,

Platforma Adopt a Pet a primit o cerere de adopție pentru animalul {pet.nume} și a fost aprobată de echipa noastră.

Pentru a valida cererea, apăsați linkul de mai jos (utilizabil o singură dată):

{link}

După validare veți primi fisa adoptatorului completată pe site (la adoptiile publice se cer anumite condiții). Adoptatorul va primi cartea de vizită a asociației (adresă, telefon, persoană de contact, program).

Dacă animalul nu mai este disponibil, nu este nevoie să faceți nimic; adoptatorul va fi anunțat separat.

Vă mulțumim și apreciem munca depusă pentru viața și bunăstarea animalelor.

Echipa Adopt a Pet
"""
    try:
        send_mail(
            subject,
            body,
            getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@adoptapet.ro"),
            [pet.ong_email.strip()],
            fail_silently=False,
        )
        adoption_request.status = "approved_platform"
        adoption_request.save(update_fields=["status"])
        return True
    except Exception:
        return False


def run_validation_link(adoption_request):
    """
    Execută acțiunile la activarea linkului de validare: trimite către ONG datele adoptatorului,
    către adoptator datele ONG, marchează cererea ca approved_ong și invalidează tokenul.
    Returnează (success, error_message).
    """
    if not adoption_request or adoption_request.status != "approved_platform":
        return False, "Cererea nu este în așteptarea validării."
    if not adoption_request.validation_token:
        return False, "Link invalid sau deja utilizat."
    pet = adoption_request.pet
    ong_email = getattr(pet, "ong_email", None) or ""
    ong_email = ong_email.strip()
    if not ong_email:
        return False, "Lipsește contactul ONG."

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@adoptapet.ro")

    # Email către ONG: fisa standard de adopție a clientului (ridicare personală = relația continuă adăpost–client)
    subject_ong = f"[Adopt a Pet] Fisa adoptator – {adoption_request.nume_complet} – {pet.nume}"
    ridicare = "Da" if adoption_request.ridicare_personala else "Nu"
    body_ong = f"""Bună ziua,

Ați validat cererea de adopție pentru {pet.nume}. Mai jos este fisa standard de adopție a clientului. Îl puteți contacta direct.

Fisa adoptator:
- Nume: {adoption_request.nume_complet}
- Email: {adoption_request.email}
- Telefon: {adoption_request.telefon}
- Adresă: {adoption_request.adresa or '—'}
- Motivație / detalii: {adoption_request.mesaj or '—'}
- Ridicare personală (clientul vine la adăpost): {ridicare}

Mulțumim,
Echipa Adopt a Pet
"""
    # Email către adoptator: cartea de vizită a asociației (adresă, telefon, persoană, program)
    subject_client = f"[Adopt a Pet] Asociația a validat cererea pentru {pet.nume}"
    lines = [
        f"Asociația care îngrijește animalul {pet.nume} a validat cererea dvs. de adopție.",
        "",
        "Cartea de vizită a asociației:",
    ]
    if getattr(pet, "ong_address", None) and pet.ong_address.strip():
        lines.append(f"Adresă: {pet.ong_address.strip()}")
    if getattr(pet, "ong_phone", None) and pet.ong_phone.strip():
        lines.append(f"Telefon: {pet.ong_phone.strip()}")
    if ong_email:
        lines.append(f"Email: {ong_email}")
    if getattr(pet, "ong_contact_person", None) and pet.ong_contact_person.strip():
        lines.append(f"Persoană de contact: {pet.ong_contact_person.strip()}")
    if getattr(pet, "ong_visiting_hours", None) and pet.ong_visiting_hours.strip():
        lines.append(f"Program vizită: {pet.ong_visiting_hours.strip()}")
    if len(lines) == 3:
        lines.append(f"Email: {ong_email}")
    if adoption_request.ridicare_personala:
        lines.extend([
            "",
            "Ați ales ridicare personală. Puteți lua legătura direct cu asociația pentru programarea vizitei și preluarea animalului.",
        ])
    else:
        lines.extend([
            "",
            "Ați solicitat transport sau alte servicii ale platformei. Vă vom sprijini în întreaga acțiune de preluare a animalului: vom lua legătura cu asociația și vă vom contacta pentru pașii următori.",
        ])
    lines.extend([
        "",
        "Prin validarea cererii de adopție vă asumați că la fiecare 6 luni veți trimite (la cererea noastră) o poză sau mai multe cu animalul, ca să verificăm că totul este în regulă. La 3 sau 6 luni veți primi un email de follow-up în care vă vom întreba de soarta animalului.",
        "",
        "Mulțumim,",
        "Echipa Adopt a Pet",
    ])
    body_client = "\n".join(lines)
    try:
        send_mail(subject_ong, body_ong, from_email, [ong_email], fail_silently=False)
        send_mail(subject_client, body_client, from_email, [adoption_request.email], fail_silently=False)
    except Exception as e:
        return False, str(e)

    adoption_request.status = "approved_ong"
    adoption_request.validation_token = None
    adoption_request.save(update_fields=["status", "validation_token"])
    return True, None


def _verificare_post_adoptie_link(adoption_request):
    """URL absolut către formularul de verificare post-adopție (folosind tokenul cererii)."""
    if not adoption_request or not getattr(adoption_request, "post_adoption_verification_token", None):
        return ""
    path = reverse(
        "verificare_post_adoptie",
        kwargs={"token": adoption_request.post_adoption_verification_token},
    )
    base = getattr(settings, "SITE_URL", "").rstrip("/") or "https://adoptapet.ro"
    return f"{base}{path}"


def send_post_adoption_followup_email(adoption_request):
    """
    Trimite email adoptatorului la 3 sau 6 luni după adopție finalizată (status approved_ong),
    în care ne interesăm de soarta animalului. Include link către formularul de verificare post-adopție.
    Apelat de comanda send_post_adoption_followups. Returnează True dacă emailul a fost trimis.
    """
    if not adoption_request or adoption_request.status != "approved_ong":
        return False
    if adoption_request.post_adoption_followup_sent_at:
        return False
    pet = adoption_request.pet
    if not adoption_request.post_adoption_verification_token:
        adoption_request.post_adoption_verification_token = secrets.token_urlsafe(32)
        adoption_request.save(update_fields=["post_adoption_verification_token"])
    link = _verificare_post_adoptie_link(adoption_request)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@adoptapet.ro")
    subject = f"[Adopt a Pet] Cum se simte {pet.nume}? Verificare post-adopție"
    body = f"""Bună ziua, {adoption_request.nume_complet},

La finalizarea adopției pentru {pet.nume} v-am anunțat că ne pasă de soarta animalului și că, periodic, vă vom contacta.

A trecut deja câteva luni de la adopție. Ne interesează cum se simte {pet.nume}, dacă s-a integrat bine în familie și dacă totul este în regulă.

Puteți răspunde direct la acest email sau completa formularul de verificare post-adopție (mesaj + opțional poze):

{link}

Vă mulțumim că ați ales adopția și că vă îngrijiți de {pet.nume}.

Cu drag,
Echipa Adopt a Pet
"""
    try:
        send_mail(
            subject,
            body,
            from_email,
            [adoption_request.email],
            fail_silently=False,
        )
        from django.utils import timezone
        adoption_request.post_adoption_followup_sent_at = timezone.now()
        adoption_request.save(update_fields=["post_adoption_followup_sent_at"])
        return True
    except Exception:
        return False
