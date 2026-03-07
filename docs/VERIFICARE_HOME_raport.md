# Verificare HOME – raport (copiabil)

**Fișier analizat:** `templates/anunturi/home_v2.html`  
**Data raport:** martie 2026  
**Fără modificări – doar analiză.**

---

## 1. Blocuri existente în home_v2.html

| Bloc | Există | Liniile (aprox.) |
|------|--------|-------------------|
| block title | Da | 4 |
| block body_class | Da | 6 |
| block extra_css | Da | 8–10 |
| block extra_css_after | Da | 12–30 |
| block content | Da | 31–119 |
| block footer | Da | 121–158 |

**body_class** este setat pe `{% block body_class %}page-home-v2{% endblock %}` (linia 6).

---

## 2. Wrapperul principal (AW)

- **Linia 34:** `<div id="AW" class="home-v2">`
- Se află în **block content**, imediat după `{% block content %}`.

---

## 3. Comenzi / zone pentru A1, A2, A3

### În template (HTML)

- **A1** – linia 51: `<div id="A1">`  
  Conținut: badge staff „A1”, `<header class="hero-v2">` (hero-v2-bg, hero-v2-inner, logo, transport, link „Hai la noi!”).

- **A2** – linia 78: `<div id="A2">`  
  Conținut: `<div class="A2-casete-wrap">`, loop `a2_pets`, `.A2-slot`, badge A2.1–A2.12 pentru staff, link + `.A2-slot-bg` (background-image sau empty).

- **A3** – linia 95: `<div id="A3">`  
  Conținut: badge staff „A3”, `<div class="mission-bar-v2">` (adoptați, animale caută casă, link Fii parte din drum).

### În CSS inline (block extra_css_after, liniile 14–27)

- **A1:** doar în selectorul de badge: `body.page-home-v2 #A1, #A2, #A3, #A4, .home-v2-slot { position: relative; }`.
- **A2:** reguli pentru `.A2-slot`, `.A2-slot a`, `.A2-slot-bg`, `.A2-slot-bg--empty` (poze în casetă + empty).
- **A3:** același selector de badge ca pentru A1/A2/A4; nu există reguli dedicate doar pentru A3 în inline.

### În static/css/home_v2.css

- **A1:** reguli la linia 25, 124, 157, 461 (layout, culori, hero, flex).
- **A2:** reguli la 125, 158, 465, 476–583, 882, 897–918 (grid, slot, link, bg, empty, culori, responsive).
- **A3:** reguli la 126, 159, 471, 882, 930–962 (layout, mission-bar-v2, responsive).

---

## 4. Reguli CSS duplicate

### a) Între template (inline) și home_v2.css

| Selector (sau echivalent) | În template (inline) | În home_v2.css |
|---------------------------|----------------------|-----------------|
| body.page-home-v2 #A2 .A2-slot | Linia 15 (position, overflow) | 491, 550 |
| body.page-home-v2 #A2 .A2-slot a | Linia 16 (position, inset, etc.) | 554–555 |
| body.page-home-v2 #A2 .A2-slot .A2-slot-bg | Linia 17 (position, inset, background-*) | 562, 910 |
| body.page-home-v2 #A2 .A2-slot .A2-slot-bg--empty | Linia 18 (background, flex, font, padding) | 570, 918 |

Pentru A2 (.A2-slot, link, .A2-slot-bg, .A2-slot-bg--empty) există reguli atât în **inline** (liniile 15–18), cât și în **home_v2.css** (liniile de mai sus). Inline-ul are prioritate (vine după fișierul extern).

### b) Doar în home_v2.css (selectori foarte apropiați)

- **#A2 .A2-slot** – reguli la 491 și 550.
- **#A2 .A2-slot .A2-slot-bg** – la 562 și la 910 (cu .A2-casete-wrap).
- **#A2 .A2-slot .A2-slot-bg--empty** – la 570 și la 918 (cu .A2-casete-wrap).

---

## 5. Ce controlează HOME

- **a) Fișier extern:** `static/css/home_v2.css` (încărcat în block extra_css, linia 9, cu `?v=ref`).
- **b) Stiluri inline:** block `extra_css_after` din home_v2.html (liniile 12–30): un singur `<style>` cu reguli pentru A2 (slot, link, .A2-slot-bg, .A2-slot-bg--empty), badge-uri staff (A1, A2, A3, A4, .home-v2-slot) și A4 (overflow, badge mic).

---

*Raport generat pentru transmitere. Nu conține modificări de cod.*
