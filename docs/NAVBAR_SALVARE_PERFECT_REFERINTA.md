# SALVARE NAVBAR PERFECT PE TOATE PAGINILE

**DATE PENTRU MODIFICARE GREȘELI NAVBAR – REVENIRE LA ACEST PUNCT.**

---

## SALVARE CONFIRMATĂ – NAVBAR CORECT PE TOATE PAGINILE

La orice greșeală la navbar, refă valorile din acest document și din `static/css/navbar-a0-secured.css` conform specificațiilor de mai jos.

---

## VALORI SALVATE (NU SE MODIFICĂ FĂRĂ CERERE EXPLICITĂ)

| Element | Proprietate | Valoare |
|--------|-------------|---------|
| **#A0 .container** | padding-left | **5cm** |
| **#A0 .container** | padding-right | **6cm** |
| **#A0 #main_menu .a0-left** (contor) | position | **absolute** |
| **#A0 #main_menu .a0-left** | left | **-5cm** |
| **#A0 #main_menu .a0-left** | padding-left | **0.3cm** |
| **#A0 #main_menu .a0-left** | max-width | **9cm** |
| **#A0 #menu_wrap** | margin-left | **3cm** |
| **#A0 #menu_wrap.a0-right** | margin-left | **3cm** |
| **#A0 .a0-search-right** (căutare) | right | **-6.5cm** |

---

## COMPORTAMENT

- **Contor:** afișat pe TOATE paginile (fără `{% if %}` în `navbar_a0.html`).
- **Contor:** poziționat la marginea din stânga a navbar-ului (în zona de 5cm padding), nu ia spațiu în flux.
- **Butoane (Acasă → Termeni):** margin-left **3cm** – încep la 8cm de capătul stâng (5cm padding + 3cm).
- **Căutare:** right **-6.5cm** (în zona de padding dreapta).
- **Aceleași valori** pe toate paginile – fără reguli separate pentru Home/PT pentru aceste poziții.

---

## FIȘIERE

- **CSS:** `static/css/navbar-a0-secured.css`
- **Template:** `templates/components/navbar_a0.html` (contor fără condiție pe url_name)
- **Regulă parolă Home/PT:** modificări pe Home și Prietenul tău necesită parolă (`.cursor/rules/home-pt-PAROLA-OBLIGATORIE.mdc`)

---

**SALVAT:** referință pentru reparare greșeli navbar. Nu modifica valorile fără cerere explicită.  
*Actualizat azi: meniu 3cm, căutare -6.5cm.*
