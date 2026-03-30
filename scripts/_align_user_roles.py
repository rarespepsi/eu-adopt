"""Rulare: python manage.py shell < scripts/_align_user_roles.py  (sau: Get-Content ... | python manage.py shell)"""
import os
import sys
import django

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "euadopt_final.settings")
django.setup()

from django.contrib.auth import get_user_model
from home.models import AccountProfile, UserProfile

User = get_user_model()


def get_user(username: str):
    u = User.objects.filter(username__iexact=username.strip()).first()
    if not u:
        print(f"MISSING USER (case-insensitive): {username!r}")
    return u


def set_pf(usernames: list[str]) -> None:
    for name in usernames:
        u = get_user(name)
        if not u:
            continue
        # e2e_staff rămâne cont PF de test, fără privilegii admin.
        if name.strip().lower() == "e2e_staff":
            if u.is_staff or u.is_superuser:
                u.is_staff = False
                u.is_superuser = False
                u.save(update_fields=["is_staff", "is_superuser"])
                print(f"PF cleanup admin flags: {u.username}")
        ap, _ = AccountProfile.objects.get_or_create(user=u, defaults={"role": AccountProfile.ROLE_PF})
        ap.role = AccountProfile.ROLE_PF
        ap.is_public_shelter = False
        ap.save()
        prof, _ = UserProfile.objects.get_or_create(user=u)
        prof.collaborator_type = ""
        prof.save()
        print(f"PF OK: {u.username}")


def set_org_public(usernames: list[str]) -> None:
    for name in usernames:
        u = get_user(name)
        if not u:
            continue
        ap, _ = AccountProfile.objects.get_or_create(user=u, defaults={"role": AccountProfile.ROLE_ORG})
        ap.role = AccountProfile.ROLE_ORG
        ap.is_public_shelter = True
        ap.save()
        prof, _ = UserProfile.objects.get_or_create(user=u)
        prof.collaborator_type = ""
        prof.save()
        print(f"ONG public OK: {u.username}")


def set_org_private(usernames: list[str]) -> None:
    for name in usernames:
        u = get_user(name)
        if not u:
            continue
        ap, _ = AccountProfile.objects.get_or_create(user=u, defaults={"role": AccountProfile.ROLE_ORG})
        ap.role = AccountProfile.ROLE_ORG
        ap.is_public_shelter = False
        ap.save()
        prof, _ = UserProfile.objects.get_or_create(user=u)
        prof.collaborator_type = ""
        prof.save()
        print(f"ONG privat OK: {u.username}")


def set_collab(mapping: dict[str, str]) -> None:
    for name, tip in mapping.items():
        u = get_user(name)
        if not u:
            continue
        if tip not in ("cabinet", "servicii", "magazin", "transport"):
            print(f"BAD TIP {tip} for {name}")
            continue
        ap, _ = AccountProfile.objects.get_or_create(
            user=u, defaults={"role": AccountProfile.ROLE_COLLAB}
        )
        ap.role = AccountProfile.ROLE_COLLAB
        ap.is_public_shelter = False
        ap.save()
        prof, _ = UserProfile.objects.get_or_create(user=u)
        prof.collaborator_type = tip
        prof.save()
        print(f"Colab OK: {u.username} -> {tip}")


if __name__ == "__main__":
    set_pf(["dpf", "e2e_pf", "e2e_staff"])
    set_org_public(["rarespepsi"])
    set_org_private(["radu"])
    set_collab(
        {
            "nccristescu": "cabinet",
            "dg1": "servicii",
            "dg2": "servicii",
            "dm": "magazin",
            "rares": "transport",
        }
    )
    print("Done.")
