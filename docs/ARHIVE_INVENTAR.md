# Inventar foldere `_archive` (EU-Adopt)

**Scop:** listă de referință a fișierelor păstrate în arhive. **Nu** sunt folosite de rutele active ale site-ului (template-uri / CSS / JS curente stau în afara acestor foldere).

**Generat:** inventar static al structurii proiectului. La adăugare/ștergere în arhive, actualizează manual acest fișier sau regenerează lista.

**Vezi și:** `_archive/README.md`, `DOCUMENTATIE_CURATARE.md`.

---

## 1. `_archive/` (rădăcină proiect)

| Cale | Rol |
|------|-----|
| `README.md` | Scurtă descriere arhivă rădăcină |
| `URLS_PLACEHOLDER_ARCHIVED.md` | Rută URL vechi scoase din `home/urls.py` |
| `project_snapshots/euadopt_full_backup_2026-03-31_15-06-28.zip` | Snapshot ZIP (backup) |
| `project_snapshots/snapshot_2026-03-31_15-05.txt` | Notă snapshot |
| `project_snapshots/snapshot_2026-03-31_15-06-28.txt` | Notă snapshot |

---

## 2. `templates/_archive/`

Șabloane HTML vechi (pagini, înregistrare, cont, match, analiză etc.).

```
templates/_archive/README.md
templates/_archive/maintenance.html
templates/_archive/animals/prietenul_tau_v2.html
templates/_archive/anunturi/adoption_form_page.html
templates/_archive/anunturi/adoption_request_sent.html
templates/_archive/anunturi/adoption-validated.html
templates/_archive/anunturi/analiza.html
templates/_archive/anunturi/analiza-cereri.html
templates/_archive/anunturi/beneficii-adoptie.html
templates/_archive/anunturi/beneficii-adoptie-info.html
templates/_archive/anunturi/cauta.html
templates/_archive/anunturi/contact.html
templates/_archive/anunturi/cont-adauga-animal.html
templates/_archive/anunturi/cont-bulk-add-dogs.html
templates/_archive/anunturi/cont-ong.html
templates/_archive/anunturi/cont-ong-adauga.html
templates/_archive/anunturi/cont-profil.html
templates/_archive/anunturi/includes/beneficii_partner_card.html
templates/_archive/anunturi/match_quiz.html
templates/_archive/anunturi/match_quiz_done_anon.html
templates/_archive/anunturi/match_results.html
templates/_archive/anunturi/membri-list.html
templates/_archive/anunturi/my-posted-pets.html
templates/_archive/anunturi/pet-ask.html
templates/_archive/anunturi/schema-site.html
templates/_archive/anunturi/servicii.html
templates/_archive/anunturi/shop.html
templates/_archive/anunturi/termeni.html
templates/_archive/anunturi/transport.html
templates/_archive/anunturi/verificare-post-adoptie.html
templates/_archive/anunturi/wishlist.html
templates/_archive/anunturi/wishlist_unsubscribe.html
templates/_archive/components/scales_overlay.html
templates/_archive/registration/login.html
templates/_archive/registration/password_reset_complete.html
templates/_archive/registration/password_reset_confirm.html
templates/_archive/registration/password_reset_done.html
templates/_archive/registration/password_reset_email.html
templates/_archive/registration/password_reset_form.html
templates/_archive/registration/register_choose_type.html
templates/_archive/registration/register_colaborator.html
templates/_archive/registration/register_ong.html
templates/_archive/registration/register_organizatie.html
templates/_archive/registration/register_pf.html
templates/_archive/registration/register_srl.html
templates/_archive/registration/signup.html
templates/_archive/registration/signup_verificare_telefon.html
```

---

## 3. `static/css/_archive/`

```
static/css/_archive/README.md
static/css/_archive/removed-duplicates-2026.md
static/css/_archive/auth-pages.css
static/css/_archive/pets-all-debug.css
static/css/_archive/prietenul-tau-v2.css
static/css/_archive/scales-overlay.css
static/css/_archive/style-old-burtiera-animale-layout.css
static/css/_archive/transport.css
```

---

## 4. `static/js/_archive/`

```
static/js/_archive/README.md
static/js/_archive/auth-form-errors.js
static/js/_archive/measure-home-layout.js
static/js/_archive/ro-location.js
```

---

## 5. `static/includes/js/_archive/`

```
static/includes/js/_archive/jquery.mobilemenu.js
static/includes/js/_archive/jquery.sticky.js
static/includes/js/_archive/rescue.js
```

---

## Notă

- **Snapshot-urile** din `_archive/project_snapshots/` pot fi mari (ZIP); nu le include în deploy dacă nu ai nevoie de ele pe server.
- Pentru curățare sau mutare arhive, verifică că niciun `{% include %}`, `extends` sau `static` din codul activ nu pointează către aceste căi.
