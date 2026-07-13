# Navbar A0 – stare memorată (user admin / staff)

**Data memorării:** martie 2025  
**Scop:** referință pentru restaurare după greșeli; **nu modifica** `navbar_a0.html` / `navbar-a0-secured.css` fără parolă (vezi `.cursor/rules/NAVBAR_INGHETAT.mdc`, parola **1977**).

## HTML (`templates/components/navbar_a0.html`)

- Ordinea meniului: Acasă → Prietenul tău → Servicii → Transport → Shop → **(dacă staff)** Analiza, Reclama → cont (avatar+user) → … → Termeni → Contact → **plic** (✉) → **căutare** (`.a0-search-right`).
- Staff: `{% if user.is_authenticated and user.is_staff %}` → linkuri **Analiza** (`admin_analysis_home`), **Reclama** (`reclama_staff`).
- Plicul este ultimul `<li>` în meniu înainte de `</nav>`; căutarea este **sibling** după `#menu_wrap`, în `.a0-bar-inner`.

## CSS (`static/css/navbar-a0-secured.css`) – valori cheie (layout admin)

### Container / bară

- `#A0 .container`: `padding-left: 11.8125rem`, `padding-right: 14.175rem` (vezi fișier).
- `#A0 #main_menu .a0-bar-inner`: `min-width: 0`, `max-width: 100%`.

### Căutare + distanță față de plic (override final)

Selector: `#A0 #main_menu .a0-search-right` (bloc cu comentariu „Căutarea după plic”):

- `margin-left: 0.5rem` — spațiu mic între **plic** și casetă; plicul rămâne în meniu.
- `max-width: min(8.75rem, calc(100vw - 16rem))` — casetă îngustă spre dreapta, stânga fixă față de plic, fără ieșire din pagină.
- `position: static`, `right: auto`.

### Căutare extinsă (focus / expand)

- `#A0 #main_menu .a0-search-right.a0-search-expanded`:  
  `max-width: min(35.4375rem, calc(100vw - 3rem))`.
- Input `#s` în expanded: `width` / `max-width: min(35.4375rem, calc(100vw - 3rem))`.

### Câmp căutare colapsat

- `#s`: `width: 100%`, `min-width: 0`, `max-width: 100%` (în containerul limitat mai sus).
- `.a0-search-form-inline`, `#searchform`, `.a0-search-input-wrap`: `width/max-width 100%`, `min-width: 0` unde e cazul.

### Baza (înainte de override)

- `#A0 #main_menu .a0-search-right` (primul bloc): `margin-left: 4.725rem` în sursă — **suprascris** de override-ul `0.5rem` de mai sus.
- `min-width: 0`, `flex-shrink: 1` pe `.a0-search-right`.

## Mobil hamburger (≤70em) — drawer fit-content — FINAL 13 iul 2026

**Commit:** `79c21f2` · cache `?v=20260713-menu-fit-content`

**Scop:** drawer-ul nu ocupă tot ecranul — lățime = cel mai lung label din meniu.

Selectori cheie (`@media (max-width: 70em)`):

- `#A0 #menu_wrap`, `body.a0-mobile-nav-open > #menu_wrap.a0-menu-portaled`: `width: max-content !important`, `right: auto !important`, `bottom: auto !important`, `align-items: flex-start !important`
- `ul.menu`, `li`: `width: max-content !important`, `align-items: flex-start !important`
- `li a`: `white-space: nowrap !important`
- `.a0-nav-account-link`: `grid-template-columns: 2rem max-content !important`
- `.a0-nav-ilove-start`: `inline-flex`, `flex-wrap: nowrap`

**Nu reintroduce** drawer full-width (`width: 100%` / `right: 0` / `bottom: 0` pe `#menu_wrap` mobil).

## Ce nu se schimbă fără parolă

Orice ajustare de poziție, lățime, margini, transform pe navbar A0 (desktop **și** drawer mobil) — **doar** cu cerere explicită, parola **1977** și OK de execuție.
