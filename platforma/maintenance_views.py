"""
Acces secret la site când e în pregătire.
O dată pe laptop deschizi /acces-pregatire/TOKEN/ → se setează cookie, vezi site-ul.
"""

from django.conf import settings
from django.core.signing import Signer, BadSignature
from django.shortcuts import redirect
from django.http import HttpResponseForbidden

COOKIE_NAME = "maintenance_view"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 zile


def acces_pregatire(request, token):
    secret = getattr(settings, "MAINTENANCE_SECRET", "") or ""
    if not secret or token != secret:
        return HttpResponseForbidden("Cod incorect.")

    signer = Signer()
    value = signer.sign("ok")
    response = redirect("home")
    response.set_cookie(COOKIE_NAME, value, max_age=COOKIE_MAX_AGE, httponly=True, samesite="Lax")
    return response
