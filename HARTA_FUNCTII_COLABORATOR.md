# Hartă Funcții EU-Adopt (Colaborator Oferte)

Document scurt de orientare pentru zona **Magazinul meu / Oferte**, flux public oferte și segmentarea pe subtip colaborator.

## 1) Roluri și subtipuri

- **Rol cont (`AccountProfile.role`)**
  - `pf` = persoană fizică
  - `org` = ONG / firmă / adăpost
  - `collaborator`

- **Subtip colaborator (`UserProfile.collaborator_type`)**
  - `cabinet`
  - `magazin`
  - `servicii`

- **Ordine standard actuală (aliniată cu Servicii)**
  - `cabinet` -> `magazin` -> `servicii`

## 2) Modele principale

- `UserProfile` (`home/models.py`)
  - Date profil + date firmă + `collaborator_type`.

- `AccountProfile` (`home/models.py`)
  - Rol de cont (PF/ORG/COLLAB).

- `CollaboratorServiceOffer` (`home/models.py`)
  - Oferta colaboratorului.
  - Câmpuri cheie:
    - `partner_kind` (snapshot la creare: cabinet/magazin/servicii)
    - `title`, `description`, `image`
    - `valid_from`, `valid_until`
    - `quantity_available`, `is_active`
    - `external_url` (relevant la magazin)
    - `product_sheet` (fișă produs PDF/DOC/DOCX)
    - `target_*` (filtre orientative de produs)
  - Proprietăți utile:
    - `shows_product_targeting`
    - `target_filters_are_defaults`
    - `target_filter_tag_list`

- `CollaboratorOfferClaim` (`home/models.py`)
  - Solicitare "Vreau oferta" + cod unic + snapshot cumpărător.

## 3) Helpers importante (views)

- `_collaborator_tip_partener(request)`
  - Returnează subtipul colaborator curent.

- `_parse_post_date_iso(s)`
  - Parse simplu pentru date HTML `YYYY-MM-DD`.

- `_normalize_external_url(raw)`
  - Curăță + validează URL extern (`http/https`).

- `_validate_collab_product_sheet(uploaded_file)`
  - Validează fișa produs (extensie + limită dimensiune).

- `_parse_collab_offer_target_filters(post)`
  - Extrage filtrele target din POST.

- `_collab_offer_target_filters_for_tip(tip, post)`
  - La `magazin`: ia filtrele din formular.
  - La `cabinet`/`servicii`: forțează filtrele la `all`.

- `_collab_offer_valid_public_qs(base_qs)`
  - Filtrează ofertele publice după valabilitate (data curentă RO).

- `_public_offer_request_rate_limited` + `_public_offer_request_rate_limit_touch`
  - Limite anti-abuz pe cereri publice.

## 4) Flux colaborator (CRUD oferte)

- `collab_offers_control_view` (`home/views.py`)
  - Listează ofertele subtipului curent + KPI + solicitări recente.

- `collab_offer_new_view`
  - Render fișă "Adaugă" (UI diferențiat pe subtip).

- `collab_offer_add_view`
  - Creează ofertă.
  - Reguli:
    - titlu, imagine, stoc, interval = obligatorii
    - la `magazin`: `external_url` obligatoriu
    - la `magazin`: `product_sheet` opțional (validat)
    - la `cabinet`/`servicii`: `external_url` gol, target `all`

- `collab_offer_edit_view`
  - Editează ofertă existentă.
  - Reguli similare add + reset flag-uri notificări la schimbări de stoc/perioadă.

- `collab_offer_toggle_active_view`
  - Activează/dezactivează.

- `collab_offer_delete_view`
  - Șterge oferta.

## 5) Flux public oferte

  - Lista publică de oferte valide.

- `public_offer_detail_view`
  - Detaliu ofertă.
  - Pentru `magazin`:
    - buton link extern produs
    - buton "Citește fișa produsului" dacă există `product_sheet`

- `public_offer_request_view`
  - Cerere publică "Vreau oferta":
    - verificări activ/valabil/stoc
    - creare claim + cod
    - email cumpărător + email colaborator

## 6) Pagina Servicii (S3/S4/S5)

- `templates/anunturi/servicii.html`
  - S3 -> `vet_offers` (cabinet)
  - S4 -> `shop_offers` (magazin)
  - S5 -> `groom_offers` (servicii)
  - În carduri S4:
    - badge discret `PDF` dacă produsul are fișă tehnică
  - În modale:
    - buton "Deschide produsul la partener"
    - buton "Citește fișa produsului (PDF/DOC)" (doar magazin, dacă există)

## 7) Șabloane colaborator relevante

- `templates/anunturi/magazinul_meu_oferte_nou.html`
  - Fișă adăugare (UI compact, diferențiat pe subtip).

- `templates/anunturi/magazinul_meu_oferte_edit.html`
  - Fișă editare (inclusiv fișă tehnică produs la magazin).

- `templates/anunturi/magazinul_meu_oferte_control.html`
  - Tabel oferte + solicitări + filtre + preview.

- `templates/anunturi/oferta_partener_detail.html`
  - Butoane finale pentru cumpărător (produs/fișă tehnică la magazin).

## 8) Notificări automate (cron)

- Comandă: `collab_offers_run_notifications` (`home/management/commands`)
  - Dezactivează oferte expirate.
  - Reminder expirare (T-5 zile, deduplicat pe `valid_until`).
  - Reminder stoc la 1 rămas (deduplicat pe ciclu de stoc).

---

Ultima actualizare: structură cu fișă tehnică produs + aliniere ordine subtipuri colaborator.
