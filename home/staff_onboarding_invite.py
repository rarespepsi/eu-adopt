"""
Control invitații email Add USER — Faza A (log, stări) + Faza B (șabloane, valuri, plafon zilnic).

Trimiterea SMTP este dezactivată implicit (mod tehnic); activare: EUADOPT_STAFF_INVITE_EMAIL_ENABLED=1.
"""
from __future__ import annotations

import logging
import secrets
from datetime import timedelta
from typing import Any
from urllib.parse import quote

from email.utils import make_msgid

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.utils import timezone

from home.mail_helpers import _message_id_domain
from home.models import StaffOnboardingLead, StaffOnboardingInviteLog
from home.staff_onboarding_csv import is_placeholder_lead_email
from home.staff_onboarding_invite_inbound import staff_invite_reply_to_address

STAFF_INVITE_GET_PARAM = "inv"
STAFF_LEAD_INVITE_MAX_SENDS_DEFAULT = 3

_INVITE_TERMINAL_STATUSES = frozenset(
    {
        StaffOnboardingLead.INVITE_REPLIED,
        StaffOnboardingLead.INVITE_SIGNED_UP,
        StaffOnboardingLead.INVITE_BOUNCED,
        StaffOnboardingLead.INVITE_OPT_OUT,
        StaffOnboardingLead.INVITE_DO_NOT_CONTACT,
    }
)

_DISPATCH_OUTCOMES = (
    StaffOnboardingInviteLog.OUTCOME_SENT,
    StaffOnboardingInviteLog.OUTCOME_DRY_RUN,
)


def staff_invite_email_enabled() -> bool:
    return bool(getattr(settings, "STAFF_INVITE_EMAIL_ENABLED", False))


def staff_invite_cooldown_days(lead: StaffOnboardingLead) -> int:
    if lead.invite_cooldown_days is not None and lead.invite_cooldown_days >= 0:
        return int(lead.invite_cooldown_days)
    return int(getattr(settings, "STAFF_LEAD_INVITE_COOLDOWN_DAYS", 7))


def staff_invite_link_valid_days() -> int:
    return int(getattr(settings, "STAFF_LEAD_INVITE_LINK_VALID_DAYS", 7))


def staff_invite_link_expires_at(lead: StaffOnboardingLead):
    """Data expirării linkului invitație (None dacă nu s-a trimis niciodată real)."""
    sent_at = lead.invite_email_last_sent_at
    if not sent_at:
        return None
    return sent_at + timedelta(days=staff_invite_link_valid_days())


def staff_invite_is_link_expired(lead: StaffOnboardingLead, now=None) -> bool:
    now = now or timezone.now()
    expires = staff_invite_link_expires_at(lead)
    if not expires:
        return True
    return now >= expires


def staff_invite_should_rotate_token(lead: StaffOnboardingLead) -> bool:
    """Token nou la orice retrimitere (după prima trimitere reală sau simulare)."""
    if staff_invite_sent_count(lead) > 0:
        return True
    return staff_invite_is_resend_candidate(lead)


def staff_invite_rotate_token(lead: StaffOnboardingLead) -> str:
    lead.consent_invite_token = secrets.token_urlsafe(32)[:64]
    lead.save(update_fields=["consent_invite_token", "updated_at"])
    return (lead.consent_invite_token or "").strip()


def staff_invite_prepare_token_for_send(lead: StaffOnboardingLead) -> None:
    """Înainte de generarea emailului: token nou la retrimitere, altfel asigură token existent."""
    if staff_invite_should_rotate_token(lead):
        staff_invite_rotate_token(lead)
    elif not (lead.consent_invite_token or "").strip():
        lead.save(update_fields=["consent_invite_token", "updated_at"])


def staff_invite_lead_for_token(token: str) -> StaffOnboardingLead | None:
    token = (token or "").strip()
    if not token or len(token) > 72:
        return None
    return StaffOnboardingLead.objects.filter(
        consent_invite_token=token,
        imported_user__isnull=True,
    ).first()


def staff_invite_token_usable(lead: StaffOnboardingLead, now=None) -> bool:
    """Link valid: trimis real, neexpirat, fără cont creat."""
    now = now or timezone.now()
    if lead.imported_user_id:
        return False
    if not lead.invite_email_last_sent_at:
        return False
    return not staff_invite_is_link_expired(lead, now)


def staff_invite_max_sends(lead: StaffOnboardingLead) -> int:
    n = lead.invite_max_sends
    if n is None or n < 1:
        return STAFF_LEAD_INVITE_MAX_SENDS_DEFAULT
    return int(n)


def staff_invite_max_per_day() -> int:
    return int(getattr(settings, "STAFF_LEAD_INVITE_MAX_PER_DAY", 30))


def staff_invite_wave_default_size() -> int:
    return int(getattr(settings, "STAFF_LEAD_INVITE_WAVE_DEFAULT", 20))


def _day_start(now=None):
    now = now or timezone.now()
    if timezone.is_aware(now):
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def staff_invite_today_dispatch_count(now=None) -> int:
    """Trimiteri reale + simulări azi (contra plafonului zilnic)."""
    start = _day_start(now)
    return StaffOnboardingInviteLog.objects.filter(
        sent_at__gte=start,
        outcome__in=_DISPATCH_OUTCOMES,
    ).count()


def staff_invite_daily_remaining(now=None) -> int:
    return max(0, staff_invite_max_per_day() - staff_invite_today_dispatch_count(now))


def staff_invite_sent_count(lead: StaffOnboardingLead) -> int:
    return StaffOnboardingInviteLog.objects.filter(
        lead_id=lead.pk,
        outcome=StaffOnboardingInviteLog.OUTCOME_SENT,
    ).count()


def staff_invite_simulated_count(lead: StaffOnboardingLead) -> int:
    return StaffOnboardingInviteLog.objects.filter(
        lead_id=lead.pk,
        outcome=StaffOnboardingInviteLog.OUTCOME_DRY_RUN,
    ).count()


def staff_invite_display_status(lead: StaffOnboardingLead) -> str:
    if lead.imported_user_id:
        return StaffOnboardingLead.INVITE_SIGNED_UP
    return (lead.invite_mail_status or StaffOnboardingLead.INVITE_NEVER).strip() or StaffOnboardingLead.INVITE_NEVER


def staff_invite_can_send(lead: StaffOnboardingLead, now=None) -> tuple[bool, str]:
    now = now or timezone.now()
    staff_invite_sync_lead_with_site_user(lead)
    em = (lead.email or "").strip()
    if not em or is_placeholder_lead_email(em):
        return False, "fără email valid"
    if lead.imported_user_id:
        return False, "cont creat"
    st = staff_invite_display_status(lead)
    if st in _INVITE_TERMINAL_STATUSES:
        labels = dict(StaffOnboardingLead.INVITE_MAIL_STATUS_CHOICES)
        return False, labels.get(st, st)
    sent_n = staff_invite_sent_count(lead)
    max_n = staff_invite_max_sends(lead)
    if sent_n >= max_n:
        return False, f"max {max_n} trimiteri"
    if lead.invite_email_last_sent_at:
        cd = timezone.timedelta(days=staff_invite_cooldown_days(lead))
        if (now - lead.invite_email_last_sent_at) < cd:
            return False, f"cooldown {staff_invite_cooldown_days(lead)} zile"
    return True, ""


def staff_invite_sync_lead_with_site_user(lead: StaffOnboardingLead) -> bool:
    """
  Legătură automată lead → User dacă emailul e deja înregistrat pe site.
  Blochează invitațiile ulterioare (stare signed_up).
    """
    if lead.imported_user_id:
        return False
    em = (lead.email or "").strip()
    if not em or is_placeholder_lead_email(em):
        return False
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.filter(email__iexact=em).order_by("pk").first()
    if not user:
        return False
    staff_invite_mark_signed_up(lead.pk, user.pk)
    lead.refresh_from_db(fields=["imported_user_id", "invite_mail_status", "status"])
    return True


def staff_invite_sync_all_registered_leads() -> int:
    """Sincronizează toate lead-urile cu cont existent (email). Returnează număr actualizat."""
    updated = 0
    for lead in StaffOnboardingLead.objects.filter(imported_user__isnull=True).iterator():
        if staff_invite_sync_lead_with_site_user(lead):
            updated += 1
    return updated


def staff_invite_is_resend_candidate(lead: StaffOnboardingLead) -> bool:
    """Deja invitat cel puțin o dată (real sau simulare), nu prima invitație."""
    if lead.imported_user_id:
        return False
    if staff_invite_display_status(lead) == StaffOnboardingLead.INVITE_NEVER:
        return False
    if not lead.invite_email_last_sent_at and staff_invite_sent_count(lead) == 0:
        return staff_invite_simulated_count(lead) > 0
    return bool(lead.invite_email_last_sent_at or staff_invite_sent_count(lead))


def staff_invite_filter_resend_eligible_qs(qs, now=None):
    now = now or timezone.now()
    pks: list[int] = []
    for lead in qs.iterator():
        if not staff_invite_is_resend_candidate(lead):
            continue
        if staff_invite_can_send(lead, now)[0]:
            pks.append(lead.pk)
    if not pks:
        return qs.none()
    return qs.filter(pk__in=pks)


def staff_invite_count_resend_eligible(qs, now=None) -> int:
    n = 0
    for lead in qs.iterator():
        if not staff_invite_is_resend_candidate(lead):
            continue
        if staff_invite_can_send(lead, now)[0]:
            n += 1
    return n


def staff_invite_filter_eligible_qs(qs, now=None):
    now = now or timezone.now()
    pks: list[int] = []
    for lead in qs.iterator():
        if staff_invite_can_send(lead, now)[0]:
            pks.append(lead.pk)
    if not pks:
        return qs.none()
    return qs.filter(pk__in=pks)


def staff_invite_count_eligible(qs, now=None) -> int:
    n = 0
    for lead in qs.iterator():
        if staff_invite_can_send(lead, now)[0]:
            n += 1
    return n


def staff_invite_template_key(lead: StaffOnboardingLead) -> str:
    if lead.account_kind == StaffOnboardingLead.KIND_ADAPOST:
        sub = (lead.collaborator_subtype or "").strip()
        if sub == StaffOnboardingLead.COLLAB_ADPRV:
            return "adapost_adprv"
        if sub == StaffOnboardingLead.COLLAB_ADPUB or lead.is_public_shelter:
            return "adapost_adpub"
        return "adapost_adprv"
    if lead.account_kind == StaffOnboardingLead.KIND_ORG:
        return "ong"
    if lead.account_kind == StaffOnboardingLead.KIND_COLLAB:
        sub = (lead.collaborator_subtype or "").strip()
        if sub in (StaffOnboardingLead.COLLAB_CABINET, StaffOnboardingLead.COLLAB_CV):
            return "cabinet"
        if sub == StaffOnboardingLead.COLLAB_SERVICII:
            return "servicii"
        if sub == StaffOnboardingLead.COLLAB_GROOMING:
            return "grooming"
        if sub == StaffOnboardingLead.COLLAB_TRANSPORT:
            return "transport"
        if sub == StaffOnboardingLead.COLLAB_MAGAZIN:
            return "magazin"
    if lead.account_kind == StaffOnboardingLead.KIND_PF:
        return "pf"
    return "default"


def _invite_signup_url(request, lead: StaffOnboardingLead) -> str:
    if lead.account_kind == StaffOnboardingLead.KIND_PF:
        signup_path = reverse("signup_pf")
    elif lead.account_kind in (StaffOnboardingLead.KIND_ORG, StaffOnboardingLead.KIND_ADAPOST):
        signup_path = reverse("signup_organizatie")
    else:
        signup_path = reverse("signup_colaborator")
    if not (lead.consent_invite_token or "").strip():
        lead.save(update_fields=["consent_invite_token", "updated_at"])
    inv_tok = (lead.consent_invite_token or "").strip()
    signup_url = request.build_absolute_uri(signup_path)
    if inv_tok:
        signup_url = f"{signup_url}?{STAFF_INVITE_GET_PARAM}={quote(inv_tok, safe='')}"
    return signup_url


def _invite_population_min_max() -> tuple[int, int]:
    from home.population_onboarding import population_animal_max, population_animal_min

    return population_animal_min(), population_animal_max()


def _invite_link_header(org_line: str, signup_url: str, *, link_valid_until=None) -> str:
    validity_line = ""
    if link_valid_until:
        validity_line = (
            f"Linkul este valabil până la {link_valid_until.strftime('%d.%m.%Y %H:%M')} "
            f"(ora României). După această dată solicitați o invitație nouă.\n\n"
        )
    return (
        f"Bună ziua{org_line},\n\n"
        f"Creare cont EU-Adopt (link personal — apăsați aici pentru a începe):\n"
        f"{signup_url}\n\n"
        f"{validity_line}"
    )


def _invite_platform_block(loc_line: str) -> str:
    return (
        f"Vă contactăm din partea echipei EU-Adopt — singura platformă națională și "
        f"europeană dedicată adopțiilor responsabile și colaborării dintre adăposturi, "
        f"asociații, cabinete veterinare, magazine, transportatori și alte servicii "
        f"pentru animale{loc_line}.\n\n"
        f"EU-Adopt este un proiect născut din inițiativa unor iubitori de animale. "
        f"Participarea în etapa de pre-lansare este complet GRATUITĂ — fără costuri "
        f"de înregistrare, fără taxe de listare și fără comisioane pentru publicarea "
        f"animalelor în această fază.\n\n"
        f"Misiunea noastră este să oferim animalelor din grija organizațiilor de protecție "
        f"o vizibilitate mai mare și șanse reale de adopție, printr-o platformă modernă, "
        f"ușor de utilizat, cu profiluri actualizate (fotografii, date medicale, descrieri) "
        f"pentru viitorii adoptatori.\n\n"
        f"În perioada de pre-lansare (populare, validare și testare) ne propunem să "
        f"finalizăm această etapă până la începutul lunii septembrie 2026 și să pregătim "
        f"lansarea publică.\n\n"
    )


def _invite_legal_adpub_block() -> str:
    return (
        "────────────────────────────────────────\n"
        "OBLIGAȚII LEGALE — ADĂPOSTURI PUBLICE\n"
        "────────────────────────────────────────\n"
        "Conform normelor în vigoare (OUG nr. 155/2001 și HG nr. 1059/2013), operatorii "
        "adăposturilor publice au obligația de a promova adopția și revendicarea câinilor, "
        "de a informa constant populația și de a asigura transparența. În acest scop, "
        "legislația prevede, între altele: panouri de informare, website sau mijloace "
        "online de acces public la datele adăpostului, precum și organizarea periodică "
        "de târguri de adopție.\n\n"
        "EU-Adopt vă oferă un canal centralizat, modern și gratuit prin care puteți "
        "îndeplini mai ușor această obligație de promovare online a animalelor din adăpost.\n\n"
    )


def _invite_population_rules_block(*, animals: bool) -> str:
    mn, mx = _invite_population_min_max()
    lines = [
        "────────────────────────────────────────",
        "REGULI ÎN PERIOADA DE POPULARE",
        "(până la finalizarea etapei — țintă: septembrie 2026)",
        "────────────────────────────────────────",
        "În această etapă de testare și validare, vă rugăm să respectați:",
        "",
    ]
    if animals:
        lines.extend(
            [
                f"  • minimum {mn} și maximum {mx} animale publicate (câini, pisici sau alte specii);",
                "  • fiecare animal cu fișă cât mai completă: nume, vârstă, talie, sex,",
                "    date medicale (sterilizat, vaccinat, carnet, CIP unde e cazul);",
                "  • minimum 3 fotografii clare per animal;",
                "  • descriere scurtă („Cine sunt”) și trăsături de comportament bifate;",
                "  • la adăpost public: datele medicale obligatorii completate corect;",
                "  • verificați în MyPet coloana „Fișă %” — țintă 100% pentru fiecare animal;",
                "  • animalele rămân vizibile în Prietenul tău după publicare;",
                "  • fluxul de cereri adopție se activează după lansarea oficială.",
                "",
                "După finalizarea perioadei de populare și lansarea publică, veți putea adăuga",
                "mai multe animale și veți beneficia de funcționalități complete (cereri",
                "adopție, mesaje, promovare).",
            ]
        )
    else:
        lines.extend(
            [
                "  • profil de partener completat cu datele de contact actualizate;",
                "  • o ofertă sau un produs reprezentativ (după tipul de colaborator);",
                "  • detaliile pot fi extinse după lansarea oficială.",
            ]
        )
    lines.append("")
    return "\n".join(lines) + "\n\n"


def _invite_network_closing_block() -> str:
    return (
        "Ne dorim o comunitate activă la nivel național și european. Vă încurajăm "
        "să recomandați proiectul partenerilor dumneavoastră — cabinete veterinare, "
        "magazine, transportatori, groomeri, pensiuni — astfel încât animalele din "
        "grija organizațiilor participante să beneficieze de cât mai multă vizibilitate.\n\n"
        "În perioada de testare, vă rugăm să ne semnalați orice eroare, blocaj sau "
        "informație afișată incorect. Observațiile dumneavoastră ne ajută să îmbunătățim "
        "platforma înainte de lansare.\n\n"
        "Vă mulțumim pentru activitatea desfășurată în sprijinul animalelor. Sperăm să "
        "construim împreună mai multe șanse pentru fiecare câine și fiecare pisică să își "
        "găsească o familie.\n\n"
    )


def _invite_footer_block(terms_url: str, privacy_url: str) -> str:
    return (
        f"Documente legale:\n"
        f"- Termeni și condiții: {terms_url}\n"
        f"- Politica de confidențialitate (GDPR): {privacy_url}\n\n"
        f"Dacă nu doriți să fiți contactat, răspundeți la acest email cu „nu contacta”.\n\n"
        f"Cu respect,\n"
        f"Echipa EU-Adopt\n"
        f"www.eu-adopt.ro\n"
        f"contact@eu-adopt.ro\n"
    )


def _invite_middle_block(template_key: str, org_line: str, loc_line: str) -> str:
    if template_key == "adapost_adpub":
        return (
            f"Ca adăpost public{loc_line}, prin EU-Adopt puteți publica și administra "
            f"profilurile animalelor disponibile pentru adopție în zona MyPet. Promovarea "
            f"activă a animalelor din adăpost este una dintre cele mai eficiente modalități "
            f"de creștere a numărului de adopții și de reducere a timpului petrecut în adăpost.\n\n"
            + _invite_legal_adpub_block()
        )
    if template_key == "adapost_adprv":
        return (
            f"Ca adăpost privat{loc_line}, platforma vă oferă un canal structurat de "
            f"vizibilitate națională pentru animalele aflate în grija dumneavoastră, cu "
            f"mesaje și fișe centralizate în MyPet. Recomandăm promovarea activă a "
            f"animalelor disponibile pentru adopție.\n\n"
        )
    if template_key == "ong":
        return (
            f"Organizația dumneavoastră{org_line}{loc_line} poate publica animale în adopție, "
            f"gestiona fișele în MyPet și beneficia de o rețea în formare — adăposturi, "
            f"cabinete, magazine și transportatori — care sporesc vizibilitatea animalelor "
            f"din programele dumneavoastră.\n\n"
        )
    if template_key == "cabinet":
        return (
            f"Cabinetul dumneavoastră{loc_line} poate fi listat ca partener colaborator "
            f"în zona Servicii, cu oferte și vizibilitate către adoptatori și deținători "
            f"de animale. EU-Adopt leagă ecosistemul adopțiilor de servicii veterinare "
            f"de încredere.\n\n"
        )
    if template_key == "servicii":
        return (
            f"Serviciul dumneavoastră{loc_line} (cazare, pensiune etc.) poate fi publicat "
            f"în zona Servicii, cu oferte vizibile comunității EU-Adopt.\n\n"
        )
    if template_key == "grooming":
        return (
            f"Activitatea dumneavoastră de grooming / îngrijire{loc_line} poate fi listată "
            f"în zona Servicii, cu oferte vizibile adoptatorilor.\n\n"
        )
    if template_key == "transport":
        return (
            f"Ca transportator autorizat{loc_line}, vă puteți înregistra în fluxul dedicat "
            f"platformei, pentru cereri de transport legate de adopții și relocări de animale.\n\n"
        )
    if template_key == "magazin":
        return (
            f"Magazinul dumneavoastră{loc_line} poate apărea în catalogul de parteneri "
            f"(produse și oferte pentru animale), vizibil adoptatorilor și iubitorilor "
            f"de animale din platformă.\n\n"
        )
    return (
        f"Vă invităm să vă înregistrați pe EU-Adopt{loc_line} și să contribuiți la "
        f"construirea rețelei naționale și europene dedicate adopțiilor responsabile.\n\n"
    )


def _invite_subject(template_key: str, kind_label: str) -> str:
    base = "EU-Adopt — invitație de colaborare (participare gratuită)"
    subjects = {
        "adapost_adpub": "EU-Adopt — adăpost public: platformă națională, participare gratuită",
        "adapost_adprv": "EU-Adopt — adăpost privat: platformă națională, participare gratuită",
        "ong": "EU-Adopt — ONG / asociație: adopții responsabile (gratuit)",
        "cabinet": "EU-Adopt — cabinet veterinar: colaborare gratuită",
        "servicii": "EU-Adopt — partener servicii animale (gratuit)",
        "grooming": "EU-Adopt — grooming / îngrijire: colaborare gratuită",
        "transport": "EU-Adopt — transportator animale: colaborare gratuită",
        "magazin": "EU-Adopt — magazin produse animale: colaborare gratuită",
    }
    return subjects.get(template_key, f"{base} ({kind_label})")


def staff_invite_subject_body(
    request, lead: StaffOnboardingLead, now=None
) -> tuple[str, str, str]:
    """Subiect, corp, cheie șablon."""
    now = now or timezone.now()
    template_key = staff_invite_template_key(lead)
    kind_label = lead.get_account_kind_display()
    org_line = ""
    if (lead.org_display_name or "").strip():
        org_line = f" pentru {lead.org_display_name.strip()}"
    signup_url = _invite_signup_url(request, lead)
    terms_url = request.build_absolute_uri(reverse("termeni"))
    privacy_url = request.build_absolute_uri(reverse("politica_confidentialitate"))
    loc_bits = [x for x in (lead.judet, lead.oras) if (x or "").strip()]
    loc_line = f" ({', '.join(loc_bits)})" if loc_bits else ""
    link_valid_until = now + timedelta(days=staff_invite_link_valid_days())

    subject = _invite_subject(template_key, kind_label)
    animals_population = template_key in ("adapost_adpub", "adapost_adprv", "ong")
    body = (
        _invite_link_header(org_line, signup_url, link_valid_until=link_valid_until)
        + _invite_platform_block(loc_line)
        + _invite_middle_block(template_key, org_line, loc_line)
        + _invite_population_rules_block(animals=animals_population)
        + _invite_network_closing_block()
        + _invite_footer_block(terms_url, privacy_url)
    )
    return subject, body, template_key


def staff_invite_campaign_stats(now=None) -> dict[str, Any]:
    now = now or timezone.now()
    start_day = _day_start(now)
    start_week = start_day - timedelta(days=7)
    logs = StaffOnboardingInviteLog.objects.all()
    sent_today = logs.filter(sent_at__gte=start_day, outcome=StaffOnboardingInviteLog.OUTCOME_SENT).count()
    sim_today = logs.filter(sent_at__gte=start_day, outcome=StaffOnboardingInviteLog.OUTCOME_DRY_RUN).count()
    sent_week = logs.filter(
        sent_at__gte=start_week,
        outcome=StaffOnboardingInviteLog.OUTCOME_SENT,
    ).count()
    sim_week = logs.filter(
        sent_at__gte=start_week,
        outcome=StaffOnboardingInviteLog.OUTCOME_DRY_RUN,
    ).count()
    signed_up = StaffOnboardingLead.objects.filter(
        invite_mail_status=StaffOnboardingLead.INVITE_SIGNED_UP,
    ).count()
    registered_total = StaffOnboardingLead.objects.filter(imported_user__isnull=False).count()
    replied_total = StaffOnboardingLead.objects.filter(
        invite_mail_status=StaffOnboardingLead.INVITE_REPLIED,
    ).count()
    bounced_total = StaffOnboardingLead.objects.filter(
        invite_mail_status=StaffOnboardingLead.INVITE_BOUNCED,
    ).count()
    blocked_total = StaffOnboardingLead.objects.filter(
        invite_mail_status__in=(
            StaffOnboardingLead.INVITE_DO_NOT_CONTACT,
            StaffOnboardingLead.INVITE_OPT_OUT,
        ),
    ).count()
    pending_leads = StaffOnboardingLead.objects.filter(imported_user__isnull=True)
    first_eligible = staff_invite_count_eligible(
        pending_leads.filter(invite_mail_status=StaffOnboardingLead.INVITE_NEVER)
    )
    resend_eligible = staff_invite_count_resend_eligible(pending_leads)
    invited_ever = (
        StaffOnboardingLead.objects.filter(
            invite_logs__outcome__in=_DISPATCH_OUTCOMES,
        )
        .distinct()
        .count()
    )
    return {
        "sent_today": sent_today,
        "sim_today": sim_today,
        "dispatch_today": sent_today + sim_today,
        "sent_week": sent_week,
        "sim_week": sim_week,
        "daily_cap": staff_invite_max_per_day(),
        "daily_remaining": staff_invite_daily_remaining(now),
        "signed_up": signed_up,
        "registered_total": registered_total,
        "replied_total": replied_total,
        "bounced_total": bounced_total,
        "blocked_total": blocked_total,
        "first_eligible": first_eligible,
        "resend_eligible": resend_eligible,
        "invited_ever": invited_ever,
    }


def staff_invite_on_real_send(lead: StaffOnboardingLead, now=None) -> None:
    now = now or timezone.now()
    lead.invite_email_last_sent_at = now
    if lead.invite_mail_status in (StaffOnboardingLead.INVITE_NEVER, "", None):
        lead.invite_mail_status = StaffOnboardingLead.INVITE_SENT
    if lead.status == StaffOnboardingLead.ST_READY:
        lead.status = StaffOnboardingLead.ST_INVITED
    lead.save(
        update_fields=[
            "invite_email_last_sent_at",
            "invite_mail_status",
            "status",
            "updated_at",
        ]
    )


def _staff_invite_send_smtp(from_email: str, to_email: str, subject: str, body: str, lead: StaffOnboardingLead) -> str:
    """Trimite invitația cu Reply-To + Message-ID; returnează Message-ID."""
    msg_id = make_msgid(domain=_message_id_domain())
    headers = {
        "Message-ID": msg_id,
        "X-EUAdopt-Lead-Id": str(lead.pk),
        "X-EUAdopt-Mail": "staff-onboarding-invite",
    }
    reply_to = staff_invite_reply_to_address(lead.pk)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[to_email],
        reply_to=[reply_to],
        headers=headers,
    )
    msg.send(fail_silently=False)
    return msg_id


def staff_invite_mark_signed_up(lead_pk: int, user_id: int) -> None:
    StaffOnboardingLead.objects.filter(pk=lead_pk, imported_user__isnull=True).update(
        imported_user_id=user_id,
        status=StaffOnboardingLead.ST_IMPORTED,
        invite_mail_status=StaffOnboardingLead.INVITE_SIGNED_UP,
    )


def staff_invite_process_one(
    request,
    staff_user,
    lead: StaffOnboardingLead,
    *,
    dispatch_kind: str = StaffOnboardingInviteLog.DISPATCH_MANUAL,
    now=None,
) -> str:
    """
    Procesează un lead. Returnează: sent | simulated | blocked | error | daily_cap
    """
    now = now or timezone.now()
    ok, _reason = staff_invite_can_send(lead, now)
    if not ok:
        return "blocked"
    if staff_invite_daily_remaining(now) <= 0:
        return "daily_cap"
    em = (lead.email or "").strip()
    prev_token = (lead.consent_invite_token or "").strip()
    rotating = staff_invite_should_rotate_token(lead)
    staff_invite_prepare_token_for_send(lead)
    lead.refresh_from_db(fields=["consent_invite_token", "updated_at"])
    subj, body, template_key = staff_invite_subject_body(request, lead, now)
    mail_enabled = staff_invite_email_enabled()
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@eu-adopt.ro"
    log = logging.getLogger(__name__)

    def _revert_token_if_rotated() -> None:
        if rotating and prev_token:
            StaffOnboardingLead.objects.filter(pk=lead.pk).update(
                consent_invite_token=prev_token,
                updated_at=timezone.now(),
            )
            lead.consent_invite_token = prev_token

    if mail_enabled:
        try:
            msg_id = _staff_invite_send_smtp(from_email, em, subj, body, lead)
        except Exception as exc:
            _revert_token_if_rotated()
            log.exception("staff_invite_send lead_id=%s", lead.pk)
            StaffOnboardingInviteLog.objects.create(
                lead=lead,
                sent_by=staff_user,
                to_email=em,
                subject=subj[:255],
                outcome=StaffOnboardingInviteLog.OUTCOME_ERROR,
                error_message=str(exc)[:2000],
                template_key=template_key,
                dispatch_kind=dispatch_kind,
            )
            return "error"
        StaffOnboardingInviteLog.objects.create(
            lead=lead,
            sent_by=staff_user,
            to_email=em,
            subject=subj[:255],
            outcome=StaffOnboardingInviteLog.OUTCOME_SENT,
            template_key=template_key,
            dispatch_kind=dispatch_kind,
            message_id=msg_id[:255],
        )
        staff_invite_on_real_send(lead, now)
        return "sent"
    StaffOnboardingInviteLog.objects.create(
        lead=lead,
        sent_by=staff_user,
        to_email=em,
        subject=subj[:255],
        outcome=StaffOnboardingInviteLog.OUTCOME_DRY_RUN,
        template_key=template_key,
        dispatch_kind=dispatch_kind,
    )
    return "simulated"


def staff_invite_process_batch(
    request,
    staff_user,
    leads,
    *,
    dispatch_kind: str = StaffOnboardingInviteLog.DISPATCH_MANUAL,
    max_count: int | None = None,
) -> dict[str, int]:
    max_batch = int(getattr(settings, "STAFF_LEAD_INVITE_MAX_BATCH", 100))
    limit = max_batch if max_count is None else min(max_count, max_batch)
    stats = {
        "sent": 0,
        "simulated": 0,
        "blocked": 0,
        "error": 0,
        "daily_cap": 0,
        "invalid": 0,
    }
    processed = 0
    for lead in leads:
        if processed >= limit:
            break
        if staff_invite_daily_remaining() <= 0:
            stats["daily_cap"] += 1
            break
        result = staff_invite_process_one(
            request,
            staff_user,
            lead,
            dispatch_kind=dispatch_kind,
            now=timezone.now(),
        )
        if result == "sent":
            stats["sent"] += 1
            processed += 1
        elif result == "simulated":
            stats["simulated"] += 1
            processed += 1
        elif result == "blocked":
            stats["blocked"] += 1
        elif result == "error":
            stats["error"] += 1
        elif result == "daily_cap":
            stats["daily_cap"] += 1
            break
    return stats


def staff_invite_build_result_message(stats: dict[str, int], *, wave: bool = False) -> str:
    mail_enabled = staff_invite_email_enabled()
    prefix = "Val invitații: " if wave else ""
    parts = []
    if mail_enabled:
        if stats.get("sent"):
            parts.append(f"{prefix}trimise {stats['sent']} email.")
    else:
        if stats.get("simulated"):
            parts.append(
                f"{prefix}simulare {stats['simulated']} în jurnal (SMTP dezactivat — mod tehnic)."
            )
    if stats.get("sent") and mail_enabled and not parts:
        parts.append(f"{prefix}0 trimise.")
    if stats.get("blocked"):
        parts.append(f"blocate: {stats['blocked']}")
    if stats.get("error"):
        parts.append(f"erori: {stats['error']}")
    if stats.get("daily_cap"):
        parts.append(f"plafon zilnic ({staff_invite_max_per_day()}/zi) atins")
    if not parts:
        return f"{prefix}nicio invitație procesată."
    return " ".join(parts)
