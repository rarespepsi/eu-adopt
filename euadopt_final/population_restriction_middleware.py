"""
Restricții populare adăpost / ONG: blochează rute adopție, shop, transport etc.
pentru ROLE_ORG (nu și staff).
"""
from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect

from home.population_onboarding import (
    population_access_restricted,
    population_redirect_for_org_user,
    user_may_login_during_population,
)


class PopulationRestrictionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not population_access_restricted():
            return self.get_response(request)

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return self.get_response(request)

        ok, msg = user_may_login_during_population(user)
        if not ok:
            from django.contrib.auth import logout as auth_logout

            auth_logout(request)
            messages.error(request, msg)
            return redirect("login")

        path = request.path or "/"
        target = population_redirect_for_org_user(user, path)
        if target:
            messages.info(
                request,
                "În etapa de populare această secțiune nu este disponibilă. "
                "Folosiți MyPet pentru a adăuga animale.",
            )
            return redirect(target)

        return self.get_response(request)
