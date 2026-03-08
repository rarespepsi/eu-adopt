# T1 – Setări de bază (doar așezare, fără legături)

**Scop:** Referință pentru setările de layout/plasare ale T1 pe pagina Transport. Nu include legături, submit, API.

---

## Container T1

- **Poziție:** Coloană stânga în TW; lățime `max-content` (se strânge la conținut).
- **Centrare:** Conținut centrat orizontal și vertical în T1; `justify-content: space-evenly`, `align-items: stretch` pe `.t1-inner`.
- **Fundal T1:** `rgba(255,255,255,0.04)`, `backdrop-filter: blur(1px)` – fundal vizibil prin tot T1.

---

## Structură conținut (ordine, una sub alta)

1. **Titlu** – casetă „Transport veterinar – România”: `min-height: 3.2rem`, text centrat sus-jos și stânga-dreapta, font 1.1rem, fundal 0.4 alb.
2. **Intro** – text „Cererea este transmisă...”: casetă, fundal 0.4 alb.
3. **Județ** – casetă inline: etichetă + select (același rând).
4. **Oraș/Localitate** – casetă inline: etichetă + select.
5. **Punct plecare** – casetă: etichetă + link ALEGE DE PE HARTĂ + input.
6. **Punct sosire** – la fel.
7. **Data și ora** – casetă inline: etichetă + (dată 2/3 + oră 1/3).
8. **Nr. câini** – casetă inline: etichetă + input numeric.
9. **Buton** – TRIMITE CEREREA, full width, centrat.

Toate au **lățimea = T1** (`align-items: stretch`), **distanțe egale** pe verticală (`justify-content: space-evenly`), **fără scroll** în T1.

---

## Transparențe (fundal vizibil)

- Titlu, intro, casete, etichete, input/select: `background: rgba(255,255,255,0.4)`.
- Buton albastru: `rgba(21,101,192,0.7)`; hover `0.85`.

---

## Text

- Culoare text (în afară de buton): `#0a0a0a`; hint `#1a1a1a`; placeholder `#1a1a1a`, opacity 0.9.
- Buton: text alb `#fff`.

---

## Clase folosite (doar așezare)

- `.t1-inner`, `.t1-title`, `.t1-intro`, `.t1-form` (display: contents), `.t1-field`, `.t1-caseta`, `.t1-row-inline`, `.t1-label-row`, `.t1-label`, `.t1-input`, `.t1-select`, `.t1-input-wrap`, `.t1-date-ora-wrap`, `.t1-submit`.

**Nu se folosesc:** `.t1-row` (layout două coloane – scos).
