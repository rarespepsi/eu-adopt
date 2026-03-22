# Oferte colaborator (servicii veterinare / parteneri) — notă funcțională

Document pentru **administrare și dezvoltare**. Descrie fluxul dintre **utilizator (cumpărător)**, **colaborator (cabinet / servicii)** și platformă.

## Roluri

- **Colaborator** (cont cu tip partener cabinet / servicii / magazin): publică oferte din **Magazinul meu → Control oferte** (`/magazinul-meu/oferte/`).
- **Utilizator** (autentificat sau nu): vede ofertele în **Oferte parteneri** și în zona Servicii (unde UI-ul este înghețat separat); poate cere datele prin **„Vreau oferta”**.

## Creare și editare ofertă

- **Adaugă ofertă** (`/magazinul-meu/oferte/nou/`): obligatoriu **titlu**, **imagine**, **număr oferte valabile** (≥ 1). Opțional: descriere scurtă, preț text, discount %.
- **Editează** (`/magazinul-meu/oferte/<id>/editeaza/`): aceleași câmpuri; imaginea poate rămâne neschimbată sau fi înlocuită. **Numărul de oferte valabile nu poate fi mai mic** decât numărul de solicitări deja înregistrate pentru acea ofertă.
- **Activ / Inactiv** și **Șterge** rămân din lista de control.

## Stoc și vizibilitate publică

- Fiecare ofertă are `quantity_available` = câte **locuri** (câte apăsări „Vreau oferta” sunt permise în total).
- La fiecare solicitare reușită se creează un rând **`CollaboratorOfferClaim`** și se consumă un loc.
- Când **ultimul** loc este consumat, oferta este setată **`is_active = False`** și **nu mai apare** în listările publice (filtru `is_active=True`). Colaboratorul poate **mări stocul** la editare și apoi **reactiva** oferta din listă dacă dorește.

## Solicitarea „Vreau oferta” (public)

- **POST** către `oferte-parteneri/<id>/vreau/` (`public_offer_request_view`).
- Condiții: ofertă activă, email valid cumpărător, colaborator cu **email** setat în cont, locuri disponibile dacă stocul e definit.
- Tranzacție DB cu **`select_for_update`** pe ofertă pentru a evita depășirea stocului la cereri simultane.
- Se generează un **cod alfanumeric unic** (același în ambele emailuri).

## Emailuri

- **Cumpărător**: subiect + corp cu cod, titlu ofertă, **date cabinet** (din profil colaborator), descriere/preț/discount dacă există.
- **Colaborator**: același cod, titlu, **snapshot date cumpărător**: nume, email, telefon și localitate (din cont dacă e logat; altfel din formular unde e cazul).

Dacă trimiterea emailului eșuează (SMTP etc.), solicitarea **rămâne înregistrată**; utilizatorul poate primi mesaj de avertizare.

## Limitare abuz (rate limit)

- După solicitări **reușite**, se incrementează contoare în **cache** (Django `LocMem` implicit sau cache-ul configurat în producție):
  - max. **15** / **10 minute** / IP / **ofertă**;
  - max. **50** / **oră** / IP **global** (toate ofertele).
- La depășire: mesaj de eroare și redirect ca la celelalte erori.

*Notă:* În producție, cu mai mulți workeri, folosiți **Redis** (sau alt cache partajat) pentru ca limitele să fie consistente între procese.

## Panou colaborator (control oferte)

- Tabel: **Nr of.** (stoc setat), **Răm.** (stoc minus solicitări), legat de aceeași logică ca mai sus.
- KPI: **Solicitări** (total claims), **Locuri rămase** (sumă pe ofertele cu stoc definit).
- **Solicitări „Vreau oferta”**: tabel cu ultimele înregistrări (dată, cod, ofertă, date snapshot cumpărător).

## Model și admin

- **`CollaboratorServiceOffer`**: oferta.
- **`CollaboratorOfferClaim`**: o solicitare; câmpuri snapshot pentru audit dacă utilizatorul își schimbă datele ulterior.
- Ambele sunt vizibile în **Django Admin** (claims înregistrate pentru suport).

## Fișiere utile (cod)

- `home/models.py` — modele.
- `home/views.py` — `collab_offer_*`, `public_offer_*`, rate limit helpers.
- `home/urls.py` — rute magazin / oferte publice.
- `templates/anunturi/magazinul_meu_oferte_control.html`, `magazinul_meu_oferte_nou.html`, `magazinul_meu_oferte_edit.html`, `oferta_partener_detail.html`.
- `static/js/collab-offer-nou.js` — formular adăugare + editare (cropper / trimitere).

## Remindere email colaborator (cron)

Comandă Django (rulată **zilnic**, ex. cron sau scheduler hosting):

```bash
python manage.py collab_offers_run_notifications
```

Opțional verificare fără efect: `--dry-run`.

1. **Expirare**: ofertele cu `valid_until` **în trecut** și încă `is_active=True` sunt setate **`is_active=False`** (nu mai apar în Servicii / listări publice; rămân în lista colaboratorului).
2. **Mail expirare (max. 1 / perioadă `valid_until`)**: cu **exact 5 zile înainte** de `valid_until`, dacă oferta e activă și în fereastra de valabilitate, se trimite email colaboratorului: prelungire din cont, altfel după dată oferta dispare din Servicii. Câmp model: `expiry_notice_sent_for_valid_until` (se resetează la **schimbarea** `valid_from` / `valid_until` în fișă).
3. **Mail stoc (max. 1 / ciclu stoc)**: dacă `quantity_available > 1` și după solicitări rămâne **exact 1** loc, email opțional de tip „poți mări stocul”. Câmp: `low_stock_notice_sent` (se resetează la **schimbarea** `quantity_available` în fișă).

Link-uri din email folosesc **`SITE_BASE_URL`** din `settings` (variabilă de mediu **`EUADOPT_SITE_BASE_URL`**, fără slash final), ex. `https://www.eu-adopt.ro`.

## Panou: ofertă expirată (dată)

În tabelul de control, pe miniatura imaginii, text **„Expirată”** (oblic, semitransparent) când `valid_until < azi` (calendar România, `TIME_ZONE`).

## Ce nu face acest modul

- Nu programează în site (doar punte email + cod comun).
- Nu modifică pagina **Servicii** (înghețată în proiect fără parolă); fluxul de pe **detaliu ofertă** și **POST** este același indiferent de unde vine formularul. Ofertele expirate ies din listări publice prin `is_active=False` + filtre existente.

---

*Ultima actualizare: remindere email, dezactivare la expirare, overlay „Expirată” în panou, flag-uri deduplicare.*
