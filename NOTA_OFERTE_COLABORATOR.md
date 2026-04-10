# Oferte colaborator (servicii veterinare / parteneri) — notă funcțională

Document pentru **administrare și dezvoltare**. Descrie fluxul dintre **utilizator (cumpărător)**, **colaborator (cabinet / servicii)** și platformă.

## Roluri

- **Colaborator** (cont cu tip partener cabinet / servicii / magazin): publică oferte din **Magazinul meu → Control oferte** (`/magazinul-meu/oferte/`).
- **Utilizator** (autentificat sau nu): vede ofertele în **pagina Servicii** (`/servicii/`); nu mai există listă separată la `/oferte-parteneri/` (404). Detaliu ofertă: `/oferte-parteneri/<id>/`; poate cere datele prin **„Vreau oferta”** (POST la `oferte-parteneri/<id>/vreau/`).

## Trei fișe UI (după bifa colaboratorului)

- **`cabinet` (veterinar)** și **`servicii` (înfrumusețare):** același tip de fișă **serviciu** — fără bloc „Potrivire pentru animal”, fără câmp link produs. Titluri vizibile: *Adaugă / Editează serviciu veterinar* vs *… serviciu de înfrumusețare*.
- **`magazin`:** fișă **produs** — bloc „Potrivire pentru animal”, **link extern obligatoriu**, titluri *Adaugă / Editează produs*, buton *Publică produsul*.
- **Backend:** la `cabinet` / `servicii`, filtrele țintă sunt forțate la **„oricare”** (`all`), `external_url` gol la salvare. La `magazin` se aplică `_parse_collab_offer_target_filters` și validarea URL.
- **Model:** `shows_product_targeting` + `target_filter_tag_list` returnează etichete doar dacă `partner_kind == magazin`.

## Filtrare țintă (profil animal) — doar magazin

În fișă **magazin** (**Adaugă** / **Editează**) există blocul **„Potrivire pentru animal”** (radio): specie, talie, sex, vârstă, sterilizare. Implicit **„Oricare”**.

- **Public:** detaliu ofertă și modale Servicii — profil + link extern doar pentru `partner_kind=magazin` (`oferta_partener_detail.html`, `servicii.html` + `servicii_offer_modal_target.html` doar la magazin).
- **Migrare:** `0024_collaborator_offer_target_filters`.

## Creare și editare ofertă

- **Adaugă** (`/magazinul-meu/oferte/nou/`): câmpuri și texte în funcție de `collab_tip_partener` (vezi „Trei fișe UI”). Obligatoriu comun: **titlu**, **imagine**, **număr oferte**, **interval valabilitate**. La magazin: și **link produs** + filtre țintă.
- **Editează** (`/magazinul-meu/oferte/<id>/editeaza/`): aceleași reguli pe segment; imaginea poate rămâne neschimbată. **Numărul de oferte valabile nu poate fi mai mic** decât solicitările înregistrate.
- **Activ / Inactiv** și **Șterge** rămân din lista de control.

## Stoc și vizibilitate publică

- Fiecare ofertă are `quantity_available` = câte **locuri** (câte apăsări „Vreau oferta” sunt permise în total).
- La fiecare solicitare reușită se creează un rând **`CollaboratorOfferClaim`** și se consumă un loc.
- Când **ultimul** loc este consumat, oferta este setată **`is_active = False`** și **nu mai apare** în listările publice (filtru `is_active=True`). Colaboratorul poate **mări stocul** la editare și apoi **reactiva** oferta din listă dacă dorește.

## Canal `partner_kind` (fără amestec la schimbarea bifelor)

- Fiecare ofertă are **`partner_kind`**: `cabinet` | `servicii` | `magazin`, setat **la creare** din bifa curentă din cont.
- **Nu se schimbă** când colaboratorul își modifică tipul în profil — ofertele vechi rămân în **zona Servicii** corespunzătoare (S3 / S5 / S4).
- **Migrarea inițială** pune toate ofertele existente la `cabinet` (erau afișate doar la veterinar înainte).
- **Panoul Magazinul meu → Oferte** listează **doar** ofertele cu `partner_kind` = bifa curentă; solicitările din tabelul de jos sunt filtrate la fel.
- Link **„Vezi în Servicii”**: `#S3` (cabinet), `#S5` (servicii), `#S4` (magazin).

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
- `templates/anunturi/magazinul_meu_oferte_control.html`, `magazinul_meu_oferte_nou.html`, `magazinul_meu_oferte_edit.html`, `includes/collab_offer_target_filters_fieldset.html`, `oferta_partener_detail.html`.
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
