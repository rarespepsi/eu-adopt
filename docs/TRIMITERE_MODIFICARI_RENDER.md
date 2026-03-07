# Cum trimiți modificările pe Render (să le vezi live)

Modificările din proiect se văd pe site-ul de pe Render după ce le **incluzi în Git și le trimiți pe GitHub**. Render reface deploy-ul automat la fiecare push pe `main`.

---

## Pas 1: Deschide terminalul în rădăcina repo-ului

Repo-ul Git este pe **Desktop** (părintele folderului `adoptapet_pro`). Din PowerShell sau din Cursor (Terminal):

```powershell
cd C:\Users\USER\Desktop
```

---

## Pas 2: Verifică ce s-a schimbat

```powershell
git status
```

Vei vedea fișierele modificate (de tip `adoptapet_pro/...`).

---

## Pas 3: Adaugă doar fișierele din proiect (adoptapet_pro)

Ca să nu incluzi fișiere din restul Desktop-ului:

```powershell
git add adoptapet_pro/
```

(sau anumite fișiere: `git add adoptapet_pro/static/css/home-sidebar-compact.css adoptapet_pro/platforma/settings.py` etc.)

---

## Pas 4: Salvează (commit)

```powershell
git commit -m "Home: setări sidebar, siglă A2, logout la login, referință setări"
```

Poți schimba mesajul după ce ai modificat.

---

## Pas 5: Trimite pe GitHub (push)

```powershell
git push origin main
```

Dacă îți cere user/parolă, folosește contul GitHub. Pentru parolă poți folosi un **Personal Access Token** (GitHub → Settings → Developer settings → Personal access tokens).

---

## Pas 6: Render face deploy automat

1. Mergi pe **https://dashboard.render.com**
2. Deschide serviciul **eu-adopt** (Web Service)
3. La **Events** vei vedea un deploy nou (triggered by push)
4. Așteaptă 2–5 minute până apare **Deploy live**
5. Deschide site-ul: **https://eu-adopt.onrender.com** (sau domeniul tău custom)

---

## Dacă Render nu face deploy la push

- În Render: Web Service → **Settings** → verifică **Branch** = `main`
- Verifică că **Build & Deploy** → **Auto-Deploy** este activat (Yes)
- Dacă repo-ul e pe Desktop și proiectul în `adoptapet_pro`, în Settings → **Root Directory** pune: `adoptapet_pro`

---

## Rezumat rapid (copy-paste)

```powershell
cd C:\Users\USER\Desktop
git add adoptapet_pro/
git commit -m "Actualizări home, logout, referință setări"
git push origin main
```

Apoi verifică pe https://dashboard.render.com că deploy-ul a pornit și deschide https://eu-adopt.onrender.com după ce s-a terminat.
