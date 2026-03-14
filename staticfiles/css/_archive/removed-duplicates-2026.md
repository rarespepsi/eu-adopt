# Cod scos din fișierele active (nu executabil – doar referință)

Acest fișier conține **copii** ale regulilor șterse din style.css și pt-v2.css. Nu este încărcat de niciun template. Serveste doar pentru documentare / revenire dacă e nevoie.

---

## 1. style.css – bloc duplicat șters (fost linii ~2655-2663)

**Motiv:** `body.page-animale #PW img` apărea de două ori; același efect e acoperit de blocul de la ~6694 (cu #PW .pt-strip-item--p1 img, .pt-strip-item--p3 img, body.page-animale #PW img, etc.). Blocul de mai jos a fost șters din style.css.

```css
/* PT (#PW): pozele umplu caseta, fără goluri stânga/dreapta (anulează regula de mai sus) */
body.page-animale #PW img {
	width: 100% !important;
	height: 100% !important;
	max-width: none !important;
	object-fit: cover !important;
	object-position: center center !important;
	display: block !important;
}
```

---

## 2. pt-v2.css – bloc duplicat șters (fost linii ~777-779)

**Motiv:** Selectorul `#PW .pt-strip-item .pt-scale-mark` apărea de două ori; al doilea bloc avea doar `position: relative`. Proprietatea a fost inclusă în primul bloc, acest al doilea bloc a fost șters.

```css
#PW .pt-strip-item .pt-scale-mark {
  position: relative;
}
```

---

Data: martie 2026. Proiect nou: navbar + HOME + PT (P2 4×3).
