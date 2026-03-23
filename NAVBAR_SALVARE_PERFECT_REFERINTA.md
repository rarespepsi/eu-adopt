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

## Ce nu se schimbă fără parolă

Orice ajustare de poziție, lățime, margini, transform pe navbar A0 — **doar** cu cerere explicită și parola **1977**.
