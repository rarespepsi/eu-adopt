# Verificare domeniu .com (eu-adopt.com)

Ca **eu-adopt.com** să afișeze site-ul (aceeași aplicație ca pe eu-adopt.ro / eu-adopt.onrender.com):

---

## 1. Render – Custom Domain

1. Mergi la **https://dashboard.render.com** → Web Service **eu-adopt**
2. **Settings** → **Custom Domains** → **Add Custom Domain**
3. Adaugă: **eu-adopt.com** (și opțional **www.eu-adopt.com**)
4. Render îți arată ce înregistrări DNS trebuie setate (CNAME sau A record)

---

## 2. Variabilă de mediu ALLOWED_HOSTS

În Render → **Environment** → verifică/adaugă la **ALLOWED_HOSTS**:

```
eu-adopt.onrender.com,eu-adopt.ro,www.eu-adopt.ro,eu-adopt.com,www.eu-adopt.com
```

(fără spații; dacă ai deja valorile, adaugă doar `,eu-adopt.com,www.eu-adopt.com`)

Salvezi și faci **Manual Deploy** (sau aștepți următorul deploy) ca setările să se aplice.

---

## 3. DNS la registrarul domeniului eu-adopt.com

La providerul unde ai cumpărat **eu-adopt.com** (ex: Hostico, GoDaddy, Cloudflare etc.):

- **www.eu-adopt.com** → CNAME → `eu-adopt.onrender.com`
- **eu-adopt.com** (root @) → A record → `216.24.57.1` (IP Render)

*(Valorile exacte le vezi în Render la Custom Domains după ce adaugi domeniul.)*

---

## 4. Verificare în browser

1. Așteaptă 5–15 minute după ce ai setat DNS (propagare).
2. Deschide **https://eu-adopt.com**
3. **Prima încărcare** poate dura 30 sec – 2 min (cold start pe planul free); reîncarcă dacă dă timeout.
4. Dacă ai UptimeRobot pe eu-adopt.onrender.com, uneori și eu-adopt.com „trezește” același serviciu.

---

## Rezumat

| Unde | Ce faci |
|------|--------|
| Render → Custom Domains | Adaugi eu-adopt.com (și www) |
| Render → Environment | ALLOWED_HOSTS include eu-adopt.com,www.eu-adopt.com |
| Registrar DNS eu-adopt.com | CNAME www → eu-adopt.onrender.com; A @ → 216.24.57.1 |
| Browser | Deschizi https://eu-adopt.com (primele 1–2 min pot fi lente) |
