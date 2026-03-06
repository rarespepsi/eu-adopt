# Referință dimensiuni PT (Prietenul tău) – PW

Dimensiunile curente ale layout-ului PT, salvate pentru referință. Fișiere: `static/css/pt-v2.css`, `templates/anunturi/pets-all.html`.

---

## Grid principal (#PW .pt-grid)

| Proprietate | Valoare |
|-------------|---------|
| **grid-template-columns** | `0.26fr 3.24fr 0.5fr` (P4 \| P2 \| P5) |
| **grid-template-rows** | `0.28125fr 2.4375fr 0.28125fr` (P1 \| rând mijloc \| P3) |
| **gap** | `0` |
| **height** | `100%` |

---

## Coloane pe lățime

- **P4** (filtre + buton + publicitate): `0.26fr`
- **P2** (centru): `3.24fr`
- **P5** (dreapta): `0.5fr`

---

## Înălțimi în P4 (flex în .pt-p4-inner)

| Caseta | flex | Rol |
|--------|------|-----|
| **P4.1** (.pt-p4-box-filters) | `0.28 1 0` | Filtre (Toate, Câini, Pisici, Altele + dropdown-uri) |
| **P4.2** (.pt-p4-box-match) | `0.24 1 0` | Buton „Găsește-ți sufletul pereche” |
| **P4.3** (.pt-p4-box-ads) | `2.48 1 0` | Publicitate |

---

## Buton „Găsește-ți sufletul pereche” (inline în pets-all.html)

- **Text**: „Găsește-ți sufletul pereche” (fără emoji labuțe)
- **font-size**: `clamp(8px, 0.75vw, 14px)`
- **min-height**: `20px` (sau 26px / 30px dacă s-a modificat local)
- **padding**: `4px 16px` (sau 6px 16px dacă s-a modificat)
- **border-radius**: `8px`
- **white-space**: `nowrap`
- **background**: `#c62828`, **color**: `#fff`, **font-weight**: `700`

---

## P4 – celula (.pt-cell-4)

- **padding**: `4px`
- **align-items**: `flex-start`
- **font-size**: `1rem` (reset față de .pt-cell)
- **background**: `#8e24aa` (debug; poate fi schimbat)

---

## Titlu casetă filtre

- Text: **„Caută prietenul tău”** (fără (pisici)/(câini) în paranteză).

---

*Ultima salvare: 26.02.2025 – dimensiuni stabilizate după reducări succesive 25%, micșorare min-height buton, scoatere labuțe.*
