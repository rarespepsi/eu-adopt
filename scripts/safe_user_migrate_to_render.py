import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import transaction

from home.models import AccountProfile, UserProfile


fixture_path = Path("user_migration_sqlite.json")
if not fixture_path.exists():
    raise SystemExit("Missing user_migration_sqlite.json export file.")

data = json.loads(fixture_path.read_text(encoding="utf-8"))
by_model = {}
for obj in data:
    by_model.setdefault(obj["model"], []).append(obj)

user_rows = by_model.get("auth.user", [])
userprofile_rows = by_model.get("home.userprofile", [])
accountprofile_rows = by_model.get("home.accountprofile", [])
old_users_by_pk = {row["pk"]: row["fields"] for row in user_rows}

User = get_user_model()
old_to_new_user_id = {}

stats = {
    "users_created": 0,
    "users_skipped_username_conflict": 0,
    "users_mapped_email_conflict": 0,
    "users_unmapped": 0,
    "userprofile_created": 0,
    "userprofile_skipped_existing": 0,
    "accountprofile_created": 0,
    "accountprofile_skipped_existing": 0,
}


def map_existing_user(old_pk, old_fields):
    username = (old_fields.get("username") or "").strip()
    email = (old_fields.get("email") or "").strip()
    if not username:
        return None

    existing = User.objects.filter(username=username).first()
    if existing:
        stats["users_skipped_username_conflict"] += 1
        return existing

    if email:
        existing_email = User.objects.filter(email__iexact=email).first()
        if existing_email:
            stats["users_mapped_email_conflict"] += 1
            return existing_email
    return None


with transaction.atomic():
    for row in user_rows:
        old_pk = row["pk"]
        fields = row["fields"]
        mapped = map_existing_user(old_pk, fields)
        if mapped:
            old_to_new_user_id[old_pk] = mapped.pk
            continue

        username = (fields.get("username") or "").strip()
        if not username:
            stats["users_unmapped"] += 1
            continue

        user = User(
            username=username,
            first_name=fields.get("first_name", ""),
            last_name=fields.get("last_name", ""),
            email=fields.get("email", ""),
            is_staff=bool(fields.get("is_staff", False)),
            is_active=bool(fields.get("is_active", True)),
            is_superuser=bool(fields.get("is_superuser", False)),
        )
        # Preserve hashed password so existing credentials continue to work.
        user.password = fields.get("password", "")
        user.last_login = fields.get("last_login")
        user.date_joined = fields.get("date_joined")
        user.save()
        old_to_new_user_id[old_pk] = user.pk
        stats["users_created"] += 1

    def migrate_profile_rows(rows, model, kind):
        for row in rows:
            fields = row["fields"]
            old_user_pk = fields.get("user")
            new_user_pk = old_to_new_user_id.get(old_user_pk)
            if not new_user_pk:
                stats["users_unmapped"] += 1
                continue

            existing = model.objects.filter(user_id=new_user_pk).first()
            if existing:
                stats[f"{kind}_skipped_existing"] += 1
                continue

            payload = {"user_id": new_user_pk}
            for f in model._meta.concrete_fields:
                name = f.name
                if name in {"id", "pk", "user"}:
                    continue
                if name in fields:
                    payload[name] = fields[name]
            model.objects.create(**payload)
            stats[f"{kind}_created"] += 1

    migrate_profile_rows(userprofile_rows, UserProfile, "userprofile")
    migrate_profile_rows(accountprofile_rows, AccountProfile, "accountprofile")

print("SAFE_MIGRATION_OK")
for key, value in stats.items():
    print(f"{key}={value}")
