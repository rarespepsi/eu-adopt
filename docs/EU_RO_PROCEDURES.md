# Proceduri .ro vs hub EU — sursă de adevăr

**Modul:** `home/eu_procedures.py`  
**Context template:** `site_proc` (+ `site_proc_*`) din `eu_site_context_for_request`  
**Request:** `request.site_proc` (middleware)

Același Django + aceeași bază de animale. Pe EU prezentăm animalele și intermediăm adopțiile; pe `.ro` rămâne ecosistemul complet.

## Tabel diferențe

| Procedură | `.ro` | Hub EU (`.com` / țări) |
|-----------|-------|-------------------------|
| Catalog animale (comun) | da | da |
| Filtru țară pe PT | nu (doar RO) | da |
| Benzi cursive P1/P3 pe PT | da | **nu** (casetele P2 mai înalte) |
| Adopție: alegere ridicare / transport | da | **nu** (cerere direct) |
| Transport legat din fluxul Adopt | da | **nu** |
| Bonus oferte Servicii la adopție | da | **nu** |
| Caseta DESTINATION COUNTRY pe Transport | nu (hidden RO) | da |
| Transport: dispatch colaboratori | da | **nu** — mail la `transport@eu-adopt.ro` |
| Navbar Servicii / Shop / Coș | da | **nu** (rute blocate) |
| Transport pagină publică | da | da (standalone; hub autocar → `/custi/`) |
| `/custi/` + `/donatii/` pe hub | da | accesibile EN (preview; lansare publică donații mai târziu) |
| Cuști: layout coloane duble | layout `.ro` | pe hub: override `body.eu-site-active.page-custi` (culoar + 2×2 pe stânga/dreapta; telefon/tabletă/desktop) |
| Monedă donații / cuști | **RON (lei)** | preview tot **RON**; la **lansare publică** + **cont bancar fundație** → trecere la **EUR** (label + sume + min. alert) |
| UI limbi EN (`eu_ui`) | nu | da |

### Donații EU — monedă (TODO la deschidere)

- Acum pe hub: texte EN, sume încă în **RON** (`eu_ui.custi_currency`, `don_amt_*`, etc.).
- Când există **contul fundației** și se **deschid donațiile** public: pe EU schimbă moneda în **euro** (`.ro` rămâne lei).
- Locuri tipice: `home/eu_ui_labels.py` (`custi_*`, `don_*`), eventual flag în `home/eu_procedures.py` (`donations_currency`).

## Cum folosești

```python
from home.eu_procedures import procedures_for_request

proc = procedures_for_request(request)
if proc.adoption_skip_pickup_choice:
    ...
```

Template:

```django
{% if site_proc.adoption_skip_pickup_choice %}...{% endif %}
{% if site_proc.nav_servicii %}...{% endif %}
```

**Nu** adăuga un `if eu_site_active` nou pentru o diferență de *procedură* — adaugă un flag în `SiteProcedures` (RO + EU), apoi folosește-l.

Etichetele EN rămân în `eu_ui_labels.py` / `eu_site_active` (i18n), separate de proceduri.
