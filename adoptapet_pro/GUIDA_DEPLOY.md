# Ghid: Deploy modificări pe Render

## Modificările făcute (pagina pets-single)
- `anunturi/views.py` – view-uri pets_single, adoption_request_submit
- `anunturi/urls.py` – rute pet/<pk>/, pets-single.html
- `templates/anunturi/pets-single.html` – pagină nouă
- `anunturi/models.py` – recreat (era gol local)

---

## Pas 1: Instalează Git (dacă nu e instalat)

1. Descarcă Git: https://git-scm.com/download/win
2. Instalează (Next pe tot)
3. **Repornește Cursor** după instalare

---

## Pas 2: În Terminal (Cursor sau PowerShell)

Deschide un terminal în folderul proiectului (`c:\Users\USER\Desktop\adoptapet_pro`):

```powershell
# Verifică ce s-a schimbat
git status

# Adaugă fișierele modificate
git add anunturi/views.py anunturi/urls.py anunturi/models.py templates/anunturi/pets-single.html

# Commit
git commit -m "Adaug pagină pets-single și formular adopție"

# Push pe GitHub (render va face deploy automat)
git push origin main
```

*(Dacă branch-ul tău e `master`, schimbă `main` în `master`)*

---

## Pas 3: Alternativă – fără Git (GitHub în browser)

1. Mergi pe https://github.com/rarespepsi/eu-adopt
2. Intră în fiecare fișier modificat
3. Click pe **Edit** (creionul)
4. Copiază conținutul din fișierele locale și lipește
5. Click **Commit changes**

Fișiere de actualizat:
- `adoptapet_pro/anunturi/views.py`
- `adoptapet_pro/anunturi/urls.py`
- `adoptapet_pro/anunturi/models.py`
- `adoptapet_pro/templates/anunturi/pets-single.html`

---

## După push

Render va face deploy automat (dacă e configurat). Așteaptă 2–5 minute, apoi verifică:
- https://eu-adopt.onrender.com/pets-single.html
- https://eu-adopt.onrender.com/pet/1/
