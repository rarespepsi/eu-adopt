# Reclame furnizori pe mobil – metode

Reclamele partenerilor (A5 stânga, A6 dreapta) sunt în același template și pe mobil apar **sub** conținutul central (A1, A2, A3), cu `order: 2` și `order: 3`. Dacă nu se văd, pot fi prea mici sau utilizatorul nu scroll-ează până la ele.

---

## Metoda 1: Asigură că A5/A6 sunt vizibile și au înălțime minimă (doar CSS)

- Pe mobil, **nu** pune `display: none` pe `#home-col-left` / `#home-col-right`.
- Setează pe `.home-v2-side-inner` (în A5/A6) pe mobil: **`min-height: 120px`** (sau altă valoare) ca zonele să nu se strângă la 0.
- Opțional: un titlu scurt de tip „Partenerii noștri” deasupra casetelor, doar pe mobil.

**Avantaj:** Zero logică nouă, doar CSS.  
**Dezavantaj:** Reclamele rămân la finalul paginii; utilizatorul trebuie să dea scroll.

---

## Metoda 2: Bloc duplicat „Parteneri” vizibil doar pe mobil

- În template (ex. `home_v2.html`), adaugi un bloc care conține **aceiași** parteneri (sau un subset), plasat de exemplu **după A3** (în interiorul `.home-v2-center`).
- În CSS: pe **desktop** acest bloc are **`display: none`**; pe **mobil** are **`display: block`** (sau flex/grid). A5/A6 rămân neschimbate pe desktop.

**Avantaj:** Reclamele apar mai sus pe mobil, fără scroll mare.  
**Dezavantaj:** Conținut duplicat în HTML (același set de parteneri).

---

## Metoda 3: Bandă orizontală cu scroll (carousel) pe mobil

- Un singur rând cu logo-urile partenerilor, cu **overflow-x: auto** (scroll orizontal cu degetul).
- Poți folosi același `left_sidebar_partners` + `right_sidebar_partners` într-un container flex, cu `flex-wrap: nowrap` și `min-width` pe fiecare logo.
- Bandă vizibilă doar pe mobil (media query `max-width: 37.5em`), ascunsă pe desktop.

**Avantaj:** Vizibil, compact, bun pentru multe logo-uri.  
**Dezavantaj:** Necesită puțin CSS (și eventual JS dacă vrei navigare cu săgeți).

---

## Metoda 4: Reclame în footer (A4) pe mobil

- În `{% block footer %}`, pe mobil afișezi un rând de logo-uri partener **deasupra** sau **sub** textul din A4.
- Contexul pentru parteneri îl trimiți deja din view; îl refolosești în footer (ex. `left_sidebar_partners` + `right_sidebar_partners` sau o listă comună).

**Avantaj:** Un singur loc „dedicat” pentru reclame pe mobil.  
**Dezavantaj:** Conținut în blocul de footer; poate necesita ajustări de layout în A4.

---

## Metoda 5: Reordona doar pe mobil (CSS order)

- Fără a muta HTML-ul: pe mobil la grid-ul `.home-v2-three-cols` dai **order** diferit: de ex. A2 (grid animale) order 2, A5 order 1, A6 order 3 – astfel partenerii apar **deasupra** grid-ului de animale.
- Conform regulii proiectului (*slot-content-only*), **nu** se schimbă pozițiile coloanelor în layout; dar **order** schimbă doar ordinea de afișare în același grid, nu structura. Dacă regulile interzic orice schimbare de ordine, atunci această metodă nu se aplică.

**Avantaj:** Reclamele mai sus pe mobil, fără HTML duplicat.  
**Dezavantaj:** Poate intra în conflict cu regula „nu modificăm pozițiile”.

---

## Recomandare rapidă

- Dacă reclamele **sunt deja în pagină** dar nu se văd: **Metoda 1** (min-height pe A5/A6 pe mobil + verificare că nu sunt ascunse).
- Dacă vrei ca reclamele să fie **vizibile fără scroll** pe mobil: **Metoda 2** (bloc duplicat după A3, vizibil doar pe mobil) sau **Metoda 3** (bandă orizontală cu scroll).

Spune ce metodă preferi (sau combinație), și o putem implementa pas cu pas.
