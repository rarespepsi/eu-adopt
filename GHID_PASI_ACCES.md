# ⚠️ FIȘIER VECHI – CONȚINUT CENTRALIZAT

**📚 Acest fișier a fost centralizat în `DOCUMENTATIE_CENTRALIZATA.md`**  
**Nu mai actualiza acest fișier – folosește fișierul centralizat pentru a evita duplicarea informațiilor.**

---

# Pași: să vezi doar tu site-ul (pas cu pas)

## Pas 1 – Instalează pachetul pentru .env

În terminal (în folderul proiectului `adoptapet_pro`):

```bash
pip install python-dotenv
```

---

## Pas 2 – Verifică fișierul .env

În folderul **adoptapet_pro** (acolo unde e și `manage.py`) trebuie să existe fișierul **`.env`**.

În el sunt deja:

- `SITE_PUBLIC=False` → site-ul e „în pregătire” pentru toată lumea
- `MAINTENANCE_SECRET=eu-adopt-pregatire-2025` → codul tău secret

**Opțional:** dacă vrei un cod doar al tău, deschide `.env` și schimbă `eu-adopt-pregatire-2025` cu altceva (fără spații), de ex. `M1nC0dSecret`.

---

## Pas 3 – Pornește site-ul

În același folder (`adoptapet_pro`):

```bash
python manage.py runserver
```

Lasă fereastra deschisă. În browser **nu** deschide încă adresa de acasă.

---

## Pas 4 – Linkul secret (o singură dată pe acest laptop)

În browser deschide **exact**:

```
http://127.0.0.1:8000/acces-pregatire/eu-adopt-pregatire-2025/
```

Dacă ai schimbat codul în `.env`, pune acolo codul tău în loc de `eu-adopt-pregatire-2025`.

Apasă Enter. Ar trebui să te ducă pe pagina de acasă a site-ului (nu la „Site în pregătire”).

---

## Pas 5 – Verificare

1. Deschide un **alt browser** (sau fereastră incognito) și mergi la:
   ```
   http://127.0.0.1:8000/
   ```
   → Trebuie să vezi **„Site în pregătire”**.

2. În browserul unde ai deschis linkul secret, mergi la:
   ```
   http://127.0.0.1:8000/
   ```
   → Trebuie să vezi **site-ul normal** (acasă, animale etc.).

---

## Pe server (Render) – când pui site-ul online

1. În **Render** → serviciul tău → **Environment** (Environment Variables).
2. Adaugă:
   - **Key:** `SITE_PUBLIC` → **Value:** `False`
   - **Key:** `MAINTENANCE_SECRET` → **Value:** același cod ca în `.env` (ex. `eu-adopt-pregatire-2025`)
3. Salvează (Save). Render repornește aplicația.
4. Pe laptop deschizi o dată:
   ```
   https://URL-ul-tau-pe-Render.ro/acces-pregatire/eu-adopt-pregatire-2025/
   ```
   (înlocuiești URL-ul și codul cu ale tale.)

De atunci, doar browserul tău de pe laptop va avea acces la site; restul vor vedea „Site în pregătire”.

---

## Când vrei să lansezi site-ul pentru toată lumea

În `.env` pui:

```
SITE_PUBLIC=True
```

sau ștergi linia `SITE_PUBLIC` și în cod rămâne comportamentul implicit. Pe Render pui variabila `SITE_PUBLIC` = `True`. După asta nu mai e nevoie de link secret.
