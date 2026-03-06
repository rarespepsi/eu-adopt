# Referință layout fișă animal (poziție „perfect”)

Poziția actuală a layout-ului pentru **Adaugă animal** (cont-adauga-animal.html și cont-ong-adauga.html). Folosește acest document ca să revii la această poziție după modificări.

**Data salvată:** 22 februarie 2026

---

## Valori cheie

| Element | Proprietate | Valoare |
|--------|-------------|---------|
| **Bloc principal** | `.form-with-previews` | `margin: 1cm` (față de container), `gap: 0` (între poze și coloane) |
| **Casete poze** | `.form-photo-previews` | `width: 200px`, `margin-left: -12cm`, `gap: 0.75rem` între casete |
| **Casetă poza** | `.preview-box` | `200px × 200px`, `border: 2px solid #ddd` |
| **Zonă formular** | `.form-main` | `margin-left: 2cm` (distanță 2 cm de la lateralul casetelor poze la coloana 1), `margin-right: -15cm`, `padding-left: 5cm`, `box-sizing: border-box`, `overflow-x: visible` |
| **Grid 3 coloane** | `.form-three-cols` | `margin-left: -5cm`, `gap: 1rem` |
| **Coloana 1** | `.form-col-1` | `margin-left: 0` |
| **Coloane 2 și 3** | — | Fără margin suplimentar (în fluxul grid) |

---

## Revenire la poziție

Dacă ai modificat template-urile și vrei să revii la această poziție:

1. **cont-adauga-animal.html** și **cont-ong-adauga.html**: în blocul `<style>`, asigură-te că:
   - `.form-with-previews` are `margin: 1cm;` și `gap: 0;`
   - `.form-photo-previews` are `margin-left: -12cm;`
   - `.form-with-previews .form-main` are `margin-left: 2cm;`, `margin-right: -15cm;`, `padding-left: 5cm;`, `overflow-x: visible;`
   - `.form-three-cols` are `margin-left: -5cm;`
   - `.form-col-1` are `margin-left: 0;`

2. Pe cont-ong-adauga folosește selectorul `.adoption-form-wrap` pentru regulile de form (ex: `.adoption-form-wrap .form-three-cols`, `.adoption-form-wrap .form-col-1`), restul (`.form-with-previews`, `.form-photo-previews`, `.form-main`) rămân la fel.

---

## Fișiere

- `templates/anunturi/cont-adauga-animal.html`
- `templates/anunturi/cont-ong-adauga.html`
