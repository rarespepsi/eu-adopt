# Setări pagină Prietenul tău (salvate)

**Pagina:** `/pets-all.html` (pets_all) + varianta v2: `/prietenele-tau/` (prietenul_tau_v2).

## A0 pe Prietenul tău
- **Grafica/poziții:** aceleași ca pe home (navbar-a0-secured.css).
- **Contor:** vizibil pe home și pe Prietenul tău (În grija noastră, Adoptați).
- **Căutare:** casetă în dreapta (inline form).
- **Poziție A0:** `position: relative` pe page-animale (conținut lipit de A0, fără padding-top).
- **Contor și butoane:** în zona vizibilă (`margin-left: 0` pe .a0-left).

## Pagina pets-all (lista animale)
- **P3:** container filtre stânga (Caută prietenul tău, Sex, Talie, Județ) – `id="P3"` `data-slot="P3"`, label vizibil „P3”.
- **Caseta butoane:** „Caută prietenul tău!” – casetă cu doar butoanele Toate, Câini, Pisici, Altele (`.pets-caseta-cauta`).
- **Titlu șters:** „Prietenul tău disponibil Câini = … și Pisici = …” a fost eliminat.

## Pagina v2 (izolată)
- **Template:** `templates/animals/prietenul_tau_v2.html`.
- **CSS:** `static/css/prietenul-tau-v2.css` – grid 4/2/1 coloane, fără scroll orizontal, doar placeholder.

## Reguli
- HOME nu se modifică (vezi `.cursor/rules/home-BLOCAT-NU-MODIFICA.mdc`).
