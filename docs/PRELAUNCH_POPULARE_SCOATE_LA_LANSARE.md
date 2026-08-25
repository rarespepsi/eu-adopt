# Pre-populare / pre-lansare — ce scoatem la lansarea completă

**Scop:** toate regulile **temporare** din perioada de populare, ca să le dezactivăm ușor fără să rescriem fluxul PUB.

**Ultima actualizare:** 2026-07-16  
**Commit-uri recente flux Achiziționează:** `47b5790`, `3469f6c`

---

## 1) Oprire rapidă (recomandat pe Hetzner `.env`)

```bash
EUADOPT_PRELAUNCH_MODE=0
EUADOPT_PUBLICITATE_PRELAUNCH_FREE=0
EUADOPT_PUBLICITATE_TEMP_SUPERUSER_ONLY=0
```

Apoi: `systemctl restart euadopt`

| Env / setare | Fișier | Efect când e OFF |
|--------------|--------|------------------|
| `EUADOPT_PRELAUNCH_MODE` | `euadopt_final/settings.py` → `PRELAUNCH_MODE` | iese din pre-lansare global |
| `EUADOPT_PUBLICITATE_PRELAUNCH_FREE` | `PUBLICITATE_PRELAUNCH_FREE` | prețuri catalog reale |
| `EUADOPT_PUBLICITATE_TEMP_SUPERUSER_ONLY` | `PUBLICITATE_TEMP_SUPERUSER_ONLY` | PUB din nou pentru colaboratori (nu doar superuser) |
| `EUADOPT_PUB_MAX_SLOTS_PER_USER` | `PUBLICITATE_PRELAUNCH_MAX_SLOTS_PER_USER` | irelevant dacă free e off |
| `EUADOPT_PUB_MAX_WEEKS_PER_ORDER` | `PUBLICITATE_PRELAUNCH_MAX_WEEKS_PER_ORDER` | irelevant dacă free e off |

---

## 2) Modul central (sursă de adevăr)

**`home/prelaunch_free_access.py`**

| Funcție | Rol temporar |
|---------|----------------|
| `publicitate_prelaunch_free_enabled()` | gratuit PUB + A2 |
| `publicitate_max_slots_per_user()` | max 1 casetă/cont |
| `publicitate_max_weeks_per_order()` | max 1 bloc = 7 zile |
| `publicitate_temp_superuser_only()` / `publicitate_user_has_access()` | PUB doar superuser |
| `publicitate_user_needs_pub_nudge()` | eligibilitate nudge |
| `site_cart_skip_payment_form_enabled()` | **Achiziționează** fără formular plată |
| `PRELAUNCH_FREE_BANNER`, `PUB_PRELAUNCH_NUDGE_*` | texte UI |

La lansare: cu flag-urile de mai sus pe `0`, aceste funcții revin la comportament „normal” (fără limite free / fără skip formular).

---

## 3) Checklist UI / flux (temporar populare)

- [ ] Banner PUB „Gratuit — etapă pre-lansare · 7 zile…”
- [ ] Panou stânga compact (fără notă lungă disponibilitate; hint „Durată: 7 zile”)
- [ ] Nudge la 3 vizite (`templates/components/pub_prelaunch_nudge.html`, `static/js/pub-prelaunch-nudge.js`, context processor)
- [ ] Buton **ACHIZIȚIONEAZĂ** pe `/i-love/cos/` când total 0
- [ ] Endpoint `site_cart_free_acquire` → `/i-love/cos/achizitioneaza/`
- [ ] Redirect după Achiziționează → `/publicitate/comanda/<id>/materiale/` (sare confirmarea auxiliară)
- [ ] Soft-lock Shop / donații (`home/prelaunch_soft_lock.py`) — legat de `PRELAUNCH_MODE`

## 4) Ce NU e „temporar” (păstrează)

- Flux PUB → coș PUB → Coș General → checkout (când e plată reală)
- Catalog sloturi, comenzi, materiale creative
- Fixuri contrast (banner, buton cos verde)

---

## 5) Procedură lansare (ordine)

1. Backup DB pe H (deploy script / `backup_db_rotate.sh`).
2. Setează env-urile din §1.
3. Restart `euadopt`.
4. Verifică: colaborator vede PUB; prețuri > 0; buton **PLATESTE** + formular pe cos; fără nudge free.
5. (Opțional) ascunde/șterge componentele nudge din `base.html` dacă nu mai vrei deloc codul — nu e obligatoriu dacă flag-urile le țin inactive.

---

## 6) Agent Cursor

La cererea „scoatem regulile de populare / lansăm site-ul”: citește acest fișier + `home/prelaunch_free_access.py` + `.env` pe H; **nu** rescrie fluxul PUB de la zero.
