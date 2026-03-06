"""
Validare automată a platformei pentru cereri de adopție și trimitere email către ONG.

Verificarea de către noi se face prin condiții clare pe câmpuri/formular.
Emailul către ONG conține un link; la activare se trimit automat către ONG datele
adoptatorului și către adoptator datele de contact ONG.
"""
import logging
import re
import secrets
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)


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


def _recipient_email_for_pet(pet):
    """Emailul unde trimitem cererea de adopție: pet.ong_email sau emailul userului care a adăugat animalul."""
    if not pet:
        return None
    email = getattr(pet, "ong_email", None) or ""
    email = (email or "").strip()
    if email:
        return email
    if getattr(pet, "added_by_user_id", None) and pet.added_by_user_id:
        user = getattr(pet, "added_by_user", None)
        if user and getattr(user, "email", None):
            return (user.email or "").strip() or None
    return None


def send_adoption_request_to_ong(adoption_request, request=None):
    """
    Trimite email către ONG (pet.ong_email sau added_by_user.email) cu un link de validare.
    La activarea linkului se trimit datele adoptatorului către ONG și datele ONG către adoptator.
    Returnează True dacă emailul a fost trimis.
    """
    pet = adoption_request.pet
    if not pet:
        logger.warning("send_adoption_request_to_ong: cerere fără pet, pk=%s", getattr(adoption_request, "pk", None))
        return False
    to_email = _recipient_email_for_pet(pet)
    if not to_email:
        logger.warning("send_adoption_request_to_ong: nici ong_email nici added_by_user.email pentru pet %s (pk=%s)", pet.nume, pet.pk)
        return False
    if not adoption_request.validation_token:
        adoption_request.validation_token = secrets.token_urlsafe(32)
        adoption_request.save(update_fields=["validation_token"])
    try:
        link = _validation_link(adoption_request, request)
    except Exception as e:
        logger.exception("send_adoption_request_to_ong: eroare la construire link validare: %s", e)
        return False
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
            getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com"),
            [to_email],
            fail_silently=False,
        )
        adoption_request.status = "approved_platform"
        adoption_request.save(update_fields=["status"])
        logger.info("send_adoption_request_to_ong: email trimis la %s pentru %s (cerere pk=%s)", to_email, pet.nume, adoption_request.pk)
        # Confirmare către adoptator că cererea a fost primită
        try:
            send_adoption_request_confirmation_to_adoptor(adoption_request)
        except Exception as e:
            logger.exception("send_adoption_request_confirmation_to_adoptor: %s", e)
        return True
    except Exception as e:
        logger.exception("send_adoption_request_to_ong: trimitere email eșuată la %s: %s", to_email, e)
        return False


def send_adoption_request_confirmation_to_adoptor(adoption_request):
    """Trimite email adoptatorului: confirmare că cererea a fost primită."""
    if not adoption_request:
        return False
    pet = adoption_request.pet
    to_email = (adoption_request.email or "").strip()
    if not to_email and adoption_request.adopter:
        to_email = (adoption_request.adopter.email or "").strip()
    if not to_email:
        return False
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
    subject = f"[EU-Adopt] Cererea ta pentru {pet.nume} a fost primită"
    body = f"""Bună ziua, {adoption_request.nume_complet},

Am primit cererea ta de adopție pentru {pet.nume}. Adăpostul/proprietarul va verifica cererile și te va contacta.

Cu plăcere,
Echipa EU-Adopt
"""
    try:
        send_mail(subject, body, from_email, [to_email], fail_silently=False)
        logger.info("send_adoption_request_confirmation_to_adoptor: trimis la %s", to_email)
        return True
    except Exception as e:
        logger.exception("send_adoption_request_confirmation_to_adoptor: %s", e)
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
    ong_email = (getattr(pet, "ong_email", None) or "").strip() or _recipient_email_for_pet(pet)
    if not ong_email:
        return False, "Lipsește contactul ONG."

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")

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

    from django.utils import timezone
    adoption_request.status = "approved_ong"
    adoption_request.validation_token = None
    adoption_request.approved_at = timezone.now()
    adoption_request.save(update_fields=["status", "validation_token", "approved_at"])
    # Marchează animalul ca „în curs de adopție”
    pet.adoption_status = "reserved"
    pet.reserved_for_request = adoption_request
    pet.save(update_fields=["adoption_status", "reserved_for_request"])
    return True, None


def approve_first_adoption_request(pet):
    """
    Aprobă prima cerere pending pentru animal (FIFO). Folosește tranzacție + select_for_update.
    Returnează (success: bool, error_message: str | None, approved_request: AdoptionRequest | None).
    """
    from django.db import transaction
    from .models import AdoptionRequest

    if not pet or getattr(pet, "adoption_status", "available") not in ("available",):
        return False, "Animalul nu este disponibil pentru rezervare.", None

    with transaction.atomic():
        pet_refresh = type(pet).objects.select_for_update().get(pk=pet.pk)
        if pet_refresh.adoption_status != "available":
            return False, "Animalul a fost deja rezervat/adoptat.", None

        first_pending = (
            AdoptionRequest.objects.filter(
                pet=pet_refresh,
                status__in=("pending", "new", "approved_platform", "waitlist"),
            )
            .select_for_update()
            .order_by("data_cerere", "queue_position")
            .first()
        )
        if not first_pending:
            return False, "Nu există cereri în așteptare pentru acest animal.", None

        from django.utils import timezone
        first_pending.status = "approved"
        first_pending.approved_at = timezone.now()
        first_pending.save(update_fields=["status", "approved_at"])
        pet_refresh.adoption_status = "reserved"
        pet_refresh.reserved_for_request = first_pending
        pet_refresh.save(update_fields=["adoption_status", "reserved_for_request"])

        # Email către adoptator
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
        subject = f"[Adopt a Pet] Cererea ta pentru {pet_refresh.nume} a fost aprobată"
        body = f"""Bună ziua, {first_pending.nume_complet},

Cererea ta de adopție pentru {pet_refresh.nume} a fost aprobată. Urmează pașii pentru finalizare: contactează proprietarul/adăpostul și programează preluarea animalului.

Te vom contacta dacă sunt și alte detalii.

Mulțumim,
Echipa Adopt a Pet
"""
        try:
            send_mail(subject, body, from_email, [first_pending.email], fail_silently=False)
        except Exception as e:
            logger.exception("approve_first_adoption_request: email eșuat: %s", e)

        # Opțional: email către cei din coadă
        others = (
            AdoptionRequest.objects.filter(
                pet=pet_refresh,
                status__in=("pending", "new", "approved_platform", "waitlist"),
            )
            .exclude(pk=first_pending.pk)
            .order_by("data_cerere")
        )
        for req in others[:20]:
            try:
                send_mail(
                    f"[Adopt a Pet] {pet_refresh.nume} – ești pe lista de așteptare",
                    f"Bună ziua,\n\nAnimalul {pet_refresh.nume} este în curs de adopție. Ești pe lista de așteptare; dacă primul solicitant renunță, vei fi contactat.\n\nEchipa Adopt a Pet",
                    from_email,
                    [req.email],
                    fail_silently=True,
                )
            except Exception:
                pass

    return True, None, first_pending


def accept_adoption_request_by_owner(adoption_request):
    """
    Aprobă cererea selectată de owner (nu prima din coadă). Setează request=approved, pet=reserved,
    celelalte cereri pending/waitlist rămân sau devin waitlist. Trimite email adoptatorului acceptat + lista de așteptare.
    Returnează (success: bool, error_message: str | None).
    """
    from django.db import transaction
    from .models import AdoptionRequest

    if not adoption_request:
        return False, "Cerere invalidă."
    pet = adoption_request.pet
    if getattr(pet, "adoption_status", "available") != "available":
        return False, "Animalul nu este disponibil (deja rezervat sau adoptat)."
    if adoption_request.status not in ("pending", "new", "approved_platform", "waitlist"):
        return False, "Doar o cerere în așteptare poate fi acceptată."

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")

    with transaction.atomic():
        pet_refresh = type(pet).objects.select_for_update().get(pk=pet.pk)
        if pet_refresh.adoption_status != "available":
            return False, "Animalul a fost deja rezervat."

        req_refresh = AdoptionRequest.objects.select_for_update().get(pk=adoption_request.pk)
        if req_refresh.status not in ("pending", "new", "approved_platform", "waitlist"):
            return False, "Cererea nu mai poate fi acceptată."

        from django.utils import timezone
        req_refresh.status = "approved"
        req_refresh.approved_at = timezone.now()
        req_refresh.save(update_fields=["status", "approved_at"])
        pet_refresh.adoption_status = "reserved"
        pet_refresh.reserved_for_request = req_refresh
        pet_refresh.save(update_fields=["adoption_status", "reserved_for_request"])

        # Celelalte cereri devin waitlist
        AdoptionRequest.objects.filter(
            pet=pet_refresh,
            status__in=("pending", "new", "approved_platform"),
        ).exclude(pk=req_refresh.pk).update(status="waitlist")

        subject = f"[EU-Adopt] Cererea ta pentru {pet_refresh.nume} a fost acceptată"
        body = f"""Bună ziua, {req_refresh.nume_complet},

Cererea ta de adopție pentru {pet_refresh.nume} a fost acceptată de adăpost/proprietar. Urmează pașii: contactează adăpostul și programează preluarea animalului.

Cu plăcere,
Echipa EU-Adopt
"""
        try:
            send_mail(subject, body, from_email, [req_refresh.email], fail_silently=False)
        except Exception as e:
            logger.exception("accept_adoption_request_by_owner: email adoptator: %s", e)

        others = (
            AdoptionRequest.objects.filter(
                pet=pet_refresh,
                status="waitlist",
            )
            .exclude(pk=req_refresh.pk)
            .order_by("data_cerere")[:20]
        )
        for req in others:
            try:
                send_mail(
                    f"[EU-Adopt] {pet_refresh.nume} – ești pe lista de așteptare",
                    f"Bună ziua,\n\nAnimalul {pet_refresh.nume} este în curs de adopție. Ești pe lista de așteptare; dacă primul solicitant renunță, vei fi contactat.\n\nEchipa EU-Adopt",
                    from_email,
                    [req.email],
                    fail_silently=True,
                )
            except Exception:
                pass

    return True, None


def send_adoption_request_confirmation_to_adoptor(adoption_request):
    """
    Trimite email adoptatorului la submit cerere (confirmare: cererea a fost primită).
    """
    if not adoption_request:
        return False
    pet = adoption_request.pet
    to_email = (adoption_request.email or "").strip()
    if not to_email and adoption_request.adopter:
        to_email = (adoption_request.adopter.email or "").strip()
    if not to_email:
        return False
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
    subject = f"[EU-Adopt] Cererea ta pentru {pet.nume} a fost primită"
    body = f"""Bună ziua, {adoption_request.nume_complet},

Am primit cererea ta de adopție pentru {pet.nume}. Adăpostul/proprietarul va verifica cererile și te va contacta pentru următorii pași.

Cu plăcere,
Echipa EU-Adopt
"""
    try:
        send_mail(subject, body, from_email, [to_email], fail_silently=False)
        logger.info("send_adoption_request_confirmation_to_adoptor: trimis la %s", to_email)
        return True
    except Exception as e:
        logger.exception("send_adoption_request_confirmation_to_adoptor: %s", e)
        return False


def send_adoption_finalized_email(adoption_request):
    """
    Trimite email adoptatorului când proprietarul marchează adopția ca finalizată.
    adoption_request: cererea care trece în status finalized (cu pet, nume_complet, email).
    """
    if not adoption_request:
        return False
    pet = adoption_request.pet
    to_email = (adoption_request.email or "").strip()
    if not to_email and adoption_request.adopter:
        to_email = (adoption_request.adopter.email or "").strip()
    if not to_email:
        return False
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
    subject = f"[EU-Adopt] Adopția pentru {pet.nume} a fost finalizată"
    body = f"""Bună ziua, {adoption_request.nume_complet},

Adopția pentru {pet.nume} a fost marcată ca finalizată. Mulțumim că ai ales să adopți!

Poți accesa beneficiile pentru adoptatori (cupoane parteneri) în contul tău.

Cu plăcere,
Echipa EU-Adopt
"""
    base = getattr(settings, "SITE_URL", "").rstrip("/") or "https://adoptapet.ro"
    try:
        benefits_path = reverse("beneficii_adoptie")
        body += f"\nPagina beneficii: {base}{benefits_path}\n"
    except Exception:
        pass
    try:
        send_mail(subject, body, from_email, [to_email], fail_silently=False)
        logger.info("send_adoption_finalized_email: trimis la %s pentru request %s", to_email, adoption_request.pk)
        return True
    except Exception as e:
        logger.exception("send_adoption_finalized_email: %s", e)
        return False


def send_adoption_finalized_notice_to_owner(adoption_request):
    """Trimite email owner-ului: adopția a fost înregistrată ca finalizată."""
    if not adoption_request:
        return False
    pet = adoption_request.pet
    to_email = _recipient_email_for_pet(pet)
    if not to_email:
        return False
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
    subject = f"[EU-Adopt] Adopție finalizată: {pet.nume}"
    body = f"""Bună ziua,

Adopția pentru {pet.nume} a fost marcată ca finalizată. Adoptator: {adoption_request.nume_complet} ({adoption_request.email}).

Echipa EU-Adopt
"""
    try:
        send_mail(subject, body, from_email, [to_email], fail_silently=False)
        logger.info("send_adoption_finalized_notice_to_owner: trimis la %s", to_email)
        return True
    except Exception as e:
        logger.exception("send_adoption_finalized_notice_to_owner: %s", e)
        return False


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
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
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
