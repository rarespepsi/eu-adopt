# Agenda proiecte & programe – EU Adopt (și altele)

Documentul tău central unde notezi toate programele, conturile, domeniile și taskurile importante. **Actualizează-l pe măsură ce adaugi lucruri noi.**

---

## ⏰ MEMENTO – Diseară după 16:00

**Verifică Cloudflare + Render + eu-adopt.ro**

1. **Cloudflare** (https://dash.cloudflare.com) – dacă eu-adopt.ro e **Active** (verde)
2. **Render** → Custom Domains → apasă **Verify** la eu-adopt.ro și www.eu-adopt.ro
3. **Testează** https://eu-adopt.ro în browser

---

## 📋 Proiecte active

| Proiect | Status | Note |
|---------|--------|------|
| EU Adopt (adoptapet_pro) | 🟢 Live | https://eu-adopt.onrender.com |
| _altele..._ | | |

---

## 💻 Programe cu care lucrezi

| Program | Ce face | Link / Unde |
|---------|---------|-------------|
| **Cursor** | Editor de cod (IDE) | Deschis pe PC |
| **Python** | Limbajul aplicației | `python --version` |
| **Django** | Framework web | în proiect |
| **Git** | Versiune cod | `C:\Program Files\Git\bin\git.exe` |
| **GitHub** | Stocare cod online | https://github.com/rarespepsi/eu-adopt |
| **Render** | Hosting site + baza de date | https://dashboard.render.com |
| **PostgreSQL** | Baza de date (pe Render) | gestionat în Render |
| **PowerShell** | Terminal pentru comenzi | în Cursor sau Windows |
| **UptimeRobot** | Ține site-ul treaz (cold start) | https://uptimerobot.com |
| **Cloudinary** | Poze animale (nu se pierd la redeploy) | https://console.cloudinary.com |
| _adaugă altele..._ | | |

---

## 🌐 Domenii

| Domeniu | Registrar / Unde | Data expirării | Note |
|---------|------------------|----------------|------|
| eu-adopt.ro | Hostico | _(completăază)_ | Toate domeniile cumpărate de la Hostico. Parolă ROTLD – păstrată în siguranță. De conectat la Render. |
| _altele..._ | | | |

---

## 📧 Email & conturi principale

| Scop | Email | Notă |
|------|-------|------|
| **Social media (FB, IG, TikTok, YT)** | _(completăază)_ | ex: contact@eu-adopt.ro sau Gmail dedicat |
| **Render / GitHub** | _(completăază)_ | contul cu care te-ai înregistrat |
| _altele..._ | | |

---

## 📱 Social media (conturi de creat / de configurat)

| Platformă | Link cont | Status | User/handle |
|-----------|-----------|--------|-------------|
| Facebook (Pagină) | https://facebook.com | ⬜ de făcut | _euadopt.ro?_ |
| Instagram | https://instagram.com | ⬜ de făcut | |
| TikTok | https://tiktok.com | ⬜ de făcut | |
| YouTube | https://youtube.com | ⬜ de făcut | |
| _altele..._ | | | |

---

## ✅ De făcut (TODO)

- [ ] Configurare email principal (contact@eu-adopt.ro sau Gmail dedicat)
- [ ] Creare conturi social media cu același brand
- [ ] Conectare domeniu eu-adopt.ro la Render
- [ ] UptimeRobot configurat (dacă nu e deja)
- [ ] _(adaugă tu)_

---

## 🔗 Link-uri rapide

| Ce | Link |
|----|------|
| Site live | https://eu-adopt.onrender.com |
| Admin Django | https://eu-adopt.onrender.com/admin/ |
| Health check | https://eu-adopt.onrender.com/health/ |
| GitHub repo | https://github.com/rarespepsi/eu-adopt |
| Render dashboard | https://dashboard.render.com |
| UptimeRobot | https://uptimerobot.com |
| Cloudinary | https://console.cloudinary.com |

---

## 📝 Notițe libere

_(scrie aici orice nu ține în tabel – parole NU, doar amintiri gen „parola e în managerul X”)_

- Git pe Windows: calea completă `"C:\Program Files\Git\bin\git.exe"`
- Root Directory pe Render: `adoptapet_pro`
- Proiect local: `c:\Users\USER\Desktop\adoptapet_pro`
- **ROTLD** (pentru .ro): https://portal.rotld.ro – acolo setezi DNS-ul pentru eu-adopt.ro (parola e în emailul de înregistrare)
- **DNS eu-adopt.ro (Render):** `www` CNAME → `eu-adopt.onrender.com` | `@` A record → `216.24.57.1`
- **Cloudinary:** CLOUDINARY_URL în Render Environment (pozele merg în cloud)
- **Start Command Render:** `gunicorn platforma.wsgi:application` (nu pune migrate/seed în Start – rulează în build)
- **Animale dispar:** build-ul rulează `seed_demo_pets`; dacă lipsesc, Manual Deploy din Render

---

*Actualizat: febr. 2026 – completează pe măsură ce avansezi.*
