# Generated manually for shelter directory + public slugs

from django.db import migrations, models


def backfill_slugs(apps, schema_editor):
    AnimalListing = apps.get_model("home", "AnimalListing")
    AccountProfile = apps.get_model("home", "AccountProfile")
    UserProfile = apps.get_model("home", "UserProfile")
    import re
    import unicodedata
    from django.utils.text import slugify

    def strip_d(s):
        s = unicodedata.normalize("NFD", s or "")
        return "".join(c for c in s if unicodedata.category(c) != "Mn")

    def base_slug(*parts):
        raw = " ".join((p or "").strip() for p in parts if (p or "").strip())
        raw = strip_d(raw)
        s = slugify(raw, allow_unicode=False) or "entitate"
        return re.sub(r"-{2,}", "-", s).strip("-")[:72] or "entitate"

    used_animal = set(
        AnimalListing.objects.exclude(slug="")
        .exclude(slug__isnull=True)
        .values_list("slug", flat=True)
    )
    for listing in AnimalListing.objects.all().iterator():
        if (listing.slug or "").strip():
            used_animal.add(listing.slug)
            continue
        base = base_slug(listing.name, listing.city) or f"animal-{listing.pk}"
        cand = base
        if cand in used_animal:
            cand = f"{base}-{listing.pk}"
        n = 2
        while cand in used_animal:
            cand = f"{base}-{n}"[:90]
            n += 1
        listing.slug = cand[:90]
        listing.save(update_fields=["slug"])
        used_animal.add(cand)

    used_org = set(
        AccountProfile.objects.exclude(public_slug="")
        .exclude(public_slug__isnull=True)
        .values_list("public_slug", flat=True)
    )
    for ap in AccountProfile.objects.filter(role="org").select_related("user").iterator():
        if (ap.public_slug or "").strip():
            used_org.add(ap.public_slug)
            continue
        display = ""
        try:
            up = UserProfile.objects.filter(user_id=ap.user_id).first()
            if up:
                display = (up.company_display_name or up.company_legal_name or "").strip()
        except Exception:
            display = ""
        username = getattr(ap.user, "username", "") or f"org-{ap.user_id}"
        base = base_slug(display or username) or f"org-{ap.user_id}"
        cand = base
        if cand in used_org:
            cand = f"{base}-{ap.user_id}"
        n = 2
        while cand in used_org:
            cand = f"{base}-{n}"[:90]
            n += 1
        ap.public_slug = cand[:90]
        ap.save(update_fields=["public_slug"])
        used_org.add(cand)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0069_user_page_onboarding_seen"),
    ]

    operations = [
        migrations.AddField(
            model_name="accountprofile",
            name="public_slug",
            field=models.SlugField(
                blank=True,
                db_index=True,
                default="",
                help_text="URL: /adaposturi/<slug>/",
                max_length=90,
                verbose_name="Slug public adăpost/ONG",
            ),
        ),
        migrations.AddField(
            model_name="animallisting",
            name="slug",
            field=models.SlugField(
                blank=True,
                db_index=True,
                default="",
                help_text="URL: /caini|pisici|altele/<slug>/",
                max_length=90,
                verbose_name="Slug public",
            ),
        ),
        migrations.RunPython(backfill_slugs, noop_reverse),
    ]
