#!/usr/bin/env python
"""Creează useri de test în DB-ul local pentru Playwright (rulează din rădăcina proiectului: python e2e/create_e2e_users.py)."""
import os
import sys

import django

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "euadopt_final.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

PF_EMAIL = "e2e_pf@test.local"
PF_USERNAME = "e2e_pf"
PF_PASSWORD = "E2E_Test_Pass12!"

STAFF_EMAIL = "e2e_staff@test.local"
STAFF_USERNAME = "e2e_staff"
STAFF_PASSWORD = "E2E_Staff_Pass12!"


def main():
    if not User.objects.filter(username=PF_USERNAME).exists():
        u = User.objects.create_user(PF_USERNAME, PF_EMAIL, PF_PASSWORD)
        u.is_active = True
        u.save()
        print(f"Creat: {PF_USERNAME} ({PF_EMAIL})")
    else:
        print(f"Already exists: {PF_USERNAME}")

    if not User.objects.filter(username=STAFF_USERNAME).exists():
        s = User.objects.create_user(STAFF_USERNAME, STAFF_EMAIL, STAFF_PASSWORD)
        s.is_active = True
        s.is_staff = True
        s.save()
        print(f"Creat staff: {STAFF_USERNAME} ({STAFF_EMAIL}) -> E2E_PUB_* / publicitate")
    else:
        print(f"Already exists: {STAFF_USERNAME}")

    print("Done. PowerShell (before npm run test:e2e):")
    print(f'  $env:E2E_USER_EMAIL = "{PF_EMAIL}"')
    print(f'  $env:E2E_USER_PASSWORD = "{PF_PASSWORD}"')
    print(f'  $env:E2E_PUB_EMAIL = "{STAFF_EMAIL}"')
    print(f'  $env:E2E_PUB_PASSWORD = "{STAFF_PASSWORD}"')


if __name__ == "__main__":
    main()
