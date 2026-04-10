# Verificare backlog EU-Adopt — 2026-03-31

Listă generată din documentația din repo + scan de comentarii/șabloane. **Nu înlocuiește** verificarea în cod; bifă după ce confirmi manual.

---

## A. Conținut legal / pagini publice

- [ ] `templates/anunturi/contact.html` — înlocuit „în curs de completare” (CUI/CIF, sediu, telefon)
- [ ] `templates/anunturi/termeni_read.html` — date operator complete
- [ ] `templates/anunturi/politica_confidentialitate.html` — CUI, sediu, telefon, adresă (unde e placeholder)
- [ ] `templates/anunturi/politica_cookie.html` — adresă (și restul dacă e placeholder)
- [ ] `templates/anunturi/politica_servicii_platite.html` — adresă, telefon
- [ ] `templates/anunturi/politica_moderare.html` — adresă, telefon

---

## B. Carte site & QA (`docs/EU-ADOPT_CARTE_SITE_VERIFICARE.txt`)

- [ ] **Partea N** — matrice rol × zonă (QA manual, conform notei din fișier)
- [ ] **Apendix O, puncte 136–247** — bifate prin `test_carte_bulk` + suite + `test_carte_21_135` (sau echivalent actual)

---

## C. Pre-lansare (`e2e/PRELAUNCH_CHECKLIST.md`)

- [ ] Verificări manuale **(2)**: cont/login/signup (tipuri), anunț pe PT + fișă, MyPet scurt, servicii/colaboratori dacă e live, transport + panou operator dacă există, publicitate până la coș, legal/footer, smoke vizual pagini înghețate
- [ ] Config **(3)**: `DEBUG=False`, `SECRET_KEY` unic, HTTPS + `ALLOWED_HOSTS`, SMTP real, `collectstatic` + media, migrări pe DB producție, backup + test restore, plăți (dacă e cazul), hardening (rate limit etc.)
- [ ] Opțional **(4)**: Lighthouse/CDN, browsere extra, flux adopție cap-coadă cu email/SMS real, seed conținut

---

## D. Continuare documentată agenți (`AGENT_FISA_CONTINUITATE.md`)

- [ ] Subpagina **Requests** (Admin / Analiza) — detaliere conform „următorul pas” din ultima intrare din fișă

---

## E. Comentarii / cod — de confirmat sau implementat

- [ ] `home/views.py` — `mypet_add_view`: rafinare câmpuri + layout fișă (notă în docstring)
- [ ] `home/views.py` — publicitate: **gateway plată** (viitor; comentariu lângă catalog tarife)
- [ ] `home/views.py` — `shop_view`: verificat dacă docstring „placeholder” mai e valabil sau actualizat documentar

---

## F. `DJANGO_LISTA_ADAUGARI.md` — secțiunea „Ce nu e făcut încă”

*Verifică în codul actual; multe puncte pot fi deja rezolvate.*

- [ ] Salvare / flux „Creează cont” PF (dacă mai lipsea ceva față de starea curentă)
- [ ] Formulare ONG / Colaborator — completare backend dacă lipsea
- [ ] Legare butoane „Adoptă” → `UserAdoption` (dacă încă nu e făcută)
- [ ] Legare `UserPost` → pagini de creare postare (dacă încă nu e făcută)

---

## G. Colaboratori / oferte (`NOTA_OFERTE_COLABORATOR.md`)

- [ ] Cron zilnic: `python manage.py collab_offers_run_notifications` (pe server)
- [ ] Producție multi-worker: **Redis** (sau cache partajat) pentru rate limit la „Vreau oferta”

---

## H. Audit tehnic (`AUDIT_REPORT.md`)

- [ ] Template `templates/anunturi/analiza-animale.html` — folosit sau arhivat/șters
- [ ] `templates/anunturi/includes/harta_judete.html` — folosit sau curățat
- [ ] `templates/components/sidebar_box.html` — folosit sau curățat
- [ ] `templates/anunturi/pets-single.html` — galerie: Flexslider/Fancybox CSS vs scripturi încărcate (comportament verificat)

---

## I. Curățare opțională (`DOCUMENTATIE_CURATARE.md` §3.5)

- [ ] `static/css/style.css` — clase legacy nefolosite (ex. mențiune `pets-all-no-img`)

---

## J. Transport UI (`static/css/transport.css`)

- [ ] Sloturi T3 „rezervat viitor” — conținut când e prioritate (reclame / parteneri / CTA)

---

## K. Consistență documentație

- [ ] `DOCUMENTATIE_CURATARE.md` (§3.4) spune că în `urls.py` ar rămâne doar home + pets — **verificat față de `home/urls.py` actual**; actualizat doc dacă e depășit

---

## L. Note dev (informative, nu neapărat task produs)

- [ ] `STIK.txt` — checkpoint Transport (confirmat la nevoie)
- [ ] `docs/DEV_MOBIL_LAN.txt` — IP/lan pentru test mobil (actualizat când schimbi rețeaua)

---

*Fișier creat la 2026-03-31. Fără modificări la alte fișiere în aceeași acțiune.*
