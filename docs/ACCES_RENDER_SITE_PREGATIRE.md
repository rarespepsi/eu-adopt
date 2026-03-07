# Acces la site pe Render când afișezi „Site în pregătire”

Când **SITE_PUBLIC = False**, vizitatorii văd „Site în pregătire, lucrăm...”. Tu poți vedea site-ul live (pe Render) în două moduri:

---

## 1. Link secret (recomandat) – fără login

Ca să vezi site-ul pe **eu-adopt.onrender.com** (sau eu-adopt.ro / eu-adopt.com):

### Pas 1: Setează codul secret și pe Render

În **Render** → Web Service **eu-adopt** → **Environment** → adaugă (sau verifică):

| Key | Value |
|-----|--------|
| `MAINTENANCE_SECRET` | **Același cod ca în `.env`** (ex: `eu-adopt-pregatire-2025`) |

Salvezi. Dacă ai făcut schimbări, poți face **Manual Deploy** ca să fie sigur că e încărcat.

### Pas 2: Deschide link-ul secret **pe domeniul de pe Render**

În browser deschide (o singură dată):

```
https://eu-adopt.onrender.com/acces-pregatire/eu-adopt-pregatire-2025/
```

*(Înlocuiește `eu-adopt-pregatire-2025` cu codul tău din `.env` dacă e altul.)*

După ce se încarcă, ești redirecționat pe home și ți se setează un **cookie** (30 zile). De acum înainte, când intri pe **eu-adopt.onrender.com** (sau pe același domeniu), vezi site-ul normal, nu „În pregătire”.

**Important:** Link-ul trebuie deschis pe **URL-ul de pe Render** (eu-adopt.onrender.com), nu pe `127.0.0.1`. Pe laptop, link-ul de pe localhost îți setează cookie doar pentru local; pentru Render trebuie link pe domeniul Render.

---

## 2. Cont staff (Django)

Dacă ești logat cu un user **staff** (is_staff = True), vezi mereu site-ul, fără cookie.  
Cont staff se creează în Render → Shell: `python manage.py createsuperuser` (sau îl marchezi ca staff din admin).

---

## Rezumat

| Unde | Ce faci |
|------|--------|
| Render → Environment | `MAINTENANCE_SECRET` = același cod ca în `.env` |
| Browser | Deschizi **https://eu-adopt.onrender.com/acces-pregatire/CODUL_TAU/** o dată |
| După aceea | Vezi site-ul normal pe Render până expiră cookie-ul (30 zile) |

Local pe laptop accesul merge la fel: deschizi `http://127.0.0.1:8000/acces-pregatire/CODUL_TAU/`.  
Pe Render trebuie să folosești link-ul cu domeniul Render, ca să ți se seteze cookie-ul pentru acel domeniu.
