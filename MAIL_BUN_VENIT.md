# De ce nu am primit mailul de bun venit?

Mailul de bun venit **se trimite din cod** la fiecare creare de cont (PF, SRL, ONG).  
Dar: dacă **nu ai configurat SMTP** (serverul de email), Django **nu expediază** emailul pe internet – îl afișează doar în consolă. De aceea nu apare nimic în inbox (Gmail, Yahoo etc.).

---

## Ce trebuie să faci ca mailul să ajungă pe pagina.eu (în inbox)

### 1. Configurează trimiterea de email în `.env`

În folderul **adoptapet_pro** deschide (sau creează) fișierul **`.env`** și adaugă:

```env
# Obligatoriu: parola pentru aplicații Gmail (16 caractere, de la Google)
EMAIL_HOST_PASSWORD=xxxx-xxxx-xxxx-xxxx

# Opțional (sunt deja implicite în settings.py pentru Gmail):
# EMAIL_HOST=smtp.gmail.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=true
# EMAIL_HOST_USER=contact.euadopt@gmail.com
# DEFAULT_FROM_EMAIL=EU-Adopt <contact.euadopt@gmail.com>

# Ca linkul din mail să fie către site-ul tău
SITE_URL=https://pagina.eu
```

- **EMAIL_HOST_PASSWORD** = **Parola pentru aplicații** de la Google (vezi mai jos). **NU** parola normală de Gmail.
- Restul (host, port, user, from) sunt deja setate în `settings.py` pentru `contact.euadopt@gmail.com`. Poți suprascrie cu variabile în `.env` dacă vrei altă adresă.
- **SITE_URL** = domeniul tău (ex: `https://pagina.eu`) ca linkul „Te poți autentifica” din mail să ducă la site-ul tău.

### 2. Parola pentru aplicații (Gmail)

1. Mergi la https://myaccount.google.com/security  
2. Activează **Verificare în 2 pași** (dacă nu e deja).  
3. La **Parole pentru aplicații** → Creează parolă nouă → alege „Mail” și „Calculator”.  
4. Copiază cele 16 caractere și le pui în `.env` la **EMAIL_HOST_PASSWORD** (fără spații).

### 3. După ce ai salvat `.env`

- **Pe calculator (local):** repornește serverul Django (`python manage.py runserver`).  
- **Pe Render:** adaugă aceleași variabile la **Environment** și fă **Redeploy**.

După asta, la **orice cont nou** creat, mailul de bun venit va pleca de pe server și va ajunge în inbox.  
Poți și să retrimiți manual mailul către nccristescu și rarespepsiyahoo (se poate face printr-o comandă) – atunci îl vei primi și pe cele două adrese existente.

---

**Rezumat:** Fără `EMAIL_HOST` (și celelalte setări) în `.env`, mailul **nu pleacă** pe internet. După ce le configurezi, mailurile de bun venit vor ajunge la toate adresele (inclusiv la cele două conturi deja create, dacă rulezi din nou trimiterea).
