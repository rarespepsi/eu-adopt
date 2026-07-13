"""Pagini și PDF-uri donații (formular 230, contract sponsorizare)."""

from urllib.parse import urlencode

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from home.donatii_constants import EUADOPT_DONATION_ORG
from home.donatii_forms import ContractSponsorizareForm, Formular230Form
from home.donatii_pdf import render_contract_sponsorizare_pdf_bytes, render_formular_230_pdf_bytes
from home.models import AccountProfile, UserProfile
from home.transport_nav import transport_sursa_context


def _donatii_form_sursa(request) -> str:
    raw = request.GET.get("sursa") or request.POST.get("sursa") or ""
    return (raw or "").strip()[:96]


def _profile_for(user):
    if not user.is_authenticated:
        return None
    return UserProfile.objects.filter(user=user).first()


def _account_for(user):
    if not user.is_authenticated:
        return None
    return AccountProfile.objects.filter(user=user).first()


def _initial_formular_230(user):
    if not user.is_authenticated:
        return {}
    prof = _profile_for(user)
    initial = {
        "prenume": (user.first_name or "").strip(),
        "nume": (user.last_name or "").strip(),
        "email": (user.email or "").strip(),
        "telefon": (prof.phone or "").strip() if prof else "",
        "judet": (prof.judet or "").strip() if prof else "",
        "localitate": (prof.oras or "").strip() if prof else "",
        "adresa": (prof.donation_address or "").strip() if prof else "",
        "cnp": (prof.donation_cnp or "").strip() if prof else "",
    }
    return {k: v for k, v in initial.items() if v}


def _initial_contract(user):
    if not user.is_authenticated:
        return {}
    prof = _profile_for(user)
    if not prof:
        return {}
    return {
        "denumire_firma": (prof.company_legal_name or prof.company_display_name or "").strip(),
        "cui": (prof.company_cui or "").strip(),
        "nr_reg_com": (prof.company_reg_com or "").strip(),
        "adresa_firma": (prof.company_address or "").strip(),
        "reprezentant": (prof.company_representative or "").strip(),
    }


def _missing_pf_for_230(user) -> list[str]:
    if not user.is_authenticated:
        return []
    miss = []
    if not (user.first_name or "").strip():
        miss.append("prenume")
    if not (user.last_name or "").strip():
        miss.append("nume")
    prof = _profile_for(user)
    if prof:
        if not (prof.donation_cnp or "").strip():
            miss.append("CNP")
        if not (prof.donation_address or "").strip():
            miss.append("adresă completă")
    else:
        miss.extend(["CNP", "adresă completă"])
    return miss


def _missing_pj_for_contract(user) -> list[str]:
    if not user.is_authenticated:
        return []
    prof = _profile_for(user)
    if not prof:
        return ["profil"]
    miss = []
    if not (prof.company_legal_name or prof.company_display_name or "").strip():
        miss.append("denumire firmă")
    if not (prof.company_cui or "").strip():
        miss.append("CUI")
    if not (prof.company_reg_com or "").strip():
        miss.append("Nr. Reg. Com.")
    if not (prof.company_address or "").strip():
        miss.append("adresă firmă")
    if not (prof.company_representative or "").strip():
        miss.append("reprezentant")
    return miss


@require_http_methods(["GET", "POST"])
def donatii_formular_230_view(request):
    """Formular 230 (3,5%) — completare + PDF."""
    sursa = _donatii_form_sursa(request)
    initial = _initial_formular_230(request.user)
    missing = _missing_pf_for_230(request.user)
    profile_url = reverse("account_edit") if request.user.is_authenticated else (
        reverse("login") + "?" + urlencode({"next": reverse("donatii_formular_230")})
    )
    base_ctx = {
        "org": EUADOPT_DONATION_ORG,
        "profile_missing_fields": missing,
        "profile_complete_url": profile_url,
        "donatii_query_sursa": sursa,
    }
    base_ctx.update(transport_sursa_context(sursa))

    if request.method == "POST":
        form = Formular230Form(request.POST, user=request.user)
        if form.is_valid():
            pdf_bytes = render_formular_230_pdf_bytes(EUADOPT_DONATION_ORG, form.cleaned_data)
            if pdf_bytes is None:
                messages.error(
                    request,
                    "Generatorul PDF nu este disponibil (lipsește pachetul fpdf2). Contactează administratorul.",
                )
                return render(
                    request,
                    "donatii/formular_230.html",
                    {**base_ctx, "form": form, "donatii_show_mem_checkbox": "memoreaza_in_profil" in form.fields},
                )
            if request.user.is_authenticated and form.cleaned_data.get("memoreaza_in_profil"):
                prof, _ = UserProfile.objects.get_or_create(user=request.user)
                prof.donation_cnp = form.cleaned_data.get("cnp", "")[:13]
                prof.donation_address = (form.cleaned_data.get("adresa") or "")[:500]
                u = request.user
                u.first_name = (form.cleaned_data.get("prenume") or "")[:150]
                u.last_name = (form.cleaned_data.get("nume") or "")[:150]
                if form.cleaned_data.get("email"):
                    u.email = form.cleaned_data["email"]
                u.save()
                prof.phone = (form.cleaned_data.get("telefon") or prof.phone or "")[:20]
                prof.judet = (form.cleaned_data.get("judet") or prof.judet or "")[:120]
                prof.oras = (form.cleaned_data.get("localitate") or prof.oras or "")[:120]
                prof.save()
            resp = HttpResponse(pdf_bytes, content_type="application/pdf")
            resp["Content-Disposition"] = 'attachment; filename="Formular-230-EU-ADOPT.pdf"'
            return resp
    else:
        form = Formular230Form(initial=initial, user=request.user)

    return render(
        request,
        "donatii/formular_230.html",
        {**base_ctx, "form": form, "donatii_show_mem_checkbox": "memoreaza_in_profil" in form.fields},
    )


@require_http_methods(["GET", "POST"])
def donatii_contract_sponsorizare_view(request):
    """Contract sponsorizare firmă — completare + PDF."""
    sursa = _donatii_form_sursa(request)
    initial = _initial_contract(request.user)
    missing = _missing_pj_for_contract(request.user)
    acc = _account_for(request.user)
    is_pj_hint = bool(acc and acc.role in (AccountProfile.ROLE_ORG, AccountProfile.ROLE_COLLAB))
    profile_url = reverse("account_edit") if request.user.is_authenticated else (
        reverse("login") + "?" + urlencode({"next": reverse("donatii_contract_sponsorizare")})
    )
    base_ctx = {
        "org": EUADOPT_DONATION_ORG,
        "profile_missing_fields": missing,
        "profile_complete_url": profile_url,
        "is_pj_hint": is_pj_hint,
        "donatii_query_sursa": sursa,
    }
    base_ctx.update(transport_sursa_context(sursa))

    if request.method == "POST":
        form = ContractSponsorizareForm(request.POST, user=request.user)
        if form.is_valid():
            pdf_bytes = render_contract_sponsorizare_pdf_bytes(EUADOPT_DONATION_ORG, form.cleaned_data)
            if pdf_bytes is None:
                messages.error(
                    request,
                    "Generatorul PDF nu este disponibil (lipsește pachetul fpdf2). Contactează administratorul.",
                )
                return render(
                    request,
                    "donatii/contract_sponsorizare.html",
                    {**base_ctx, "form": form, "donatii_show_mem_checkbox": "memoreaza_in_profil" in form.fields},
                )
            if request.user.is_authenticated and form.cleaned_data.get("memoreaza_in_profil"):
                prof, _ = UserProfile.objects.get_or_create(user=request.user)
                prof.company_legal_name = (form.cleaned_data.get("denumire_firma") or "")[:255]
                prof.company_cui = (form.cleaned_data.get("cui") or "")[:32]
                prof.company_reg_com = (form.cleaned_data.get("nr_reg_com") or "")[:64]
                adf = (form.cleaned_data.get("adresa_firma") or "").strip()
                prof.company_address = adf[:255]
                prof.company_representative = (form.cleaned_data.get("reprezentant") or "")[:255]
                prof.save()
            resp = HttpResponse(pdf_bytes, content_type="application/pdf")
            resp["Content-Disposition"] = 'attachment; filename="Contract-sponsorizare-EU-ADOPT.pdf"'
            return resp
    else:
        form = ContractSponsorizareForm(initial=initial, user=request.user)

    return render(
        request,
        "donatii/contract_sponsorizare.html",
        {**base_ctx, "form": form, "donatii_show_mem_checkbox": "memoreaza_in_profil" in form.fields},
    )
