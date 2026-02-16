# Ghid configurare email – EU Adopt

Site-ul trimite emailuri la:
- **Cerere adopție** → ONG primește link de validare
- **Validare ONG** → adoptatorul primește datele asociației
- **Follow-up post-adopție** → la 3/6 luni, adoptatorul primește un email

---

## Varianta 1: Gmail (cea mai simplă)

### Pasul 1: Creează un Gmail dedicat (recomandat)

Exemple: `euadopt.contact@gmail.com` sau `contact.euadopt@gmail.com`

### Pasul 2: Activează „Parola pentru aplicații”

1. Mergi la: https://myaccount.google.com/security  
2. **Verificare în 2 pași** – trebuie să fie **activată**
3. **Parole pentru aplicații** – Creează o parolă nouă  
4. Alege „Mail” și „Calculator Windows” (sau alt dispozitiv)
5. **Copiază parola** – e o șir de 16 caractere (ex: `abcd efgh ijkl mnop`)

> ⚠️ **Nu** folosești parola normală de Gmail – Google o blochează pentru aplicații. Trebuie neapărat „Parolă pentru aplicație”.

### Pasul 3: Variabile pe Render

În Render → Web Service → **Environment** → Add:

| Key | Value |
|-----|-------|
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `true` |
| `EMAIL_HOST_USER` | `euadopt.contact@gmail.com` *(adresa ta Gmail)* |
| `EMAIL_HOST_PASSWORD` | `abcdefghijklmnop` *(parola pentru aplicație – fără spații)* |
| `DEFAULT_FROM_EMAIL` | `euadopt.contact@gmail.com` |

### Pasul 4: Redeploy

După ce adaugi variabilele, apasă **Save** – Render face redeploy automat.

---

## Varianta 2: contact@eu-adopt.ro (domeniu propriu)

Pentru adrese tip `contact@eu-adopt.ro` ai nevoie de:

1. **Serviciu de email pe domeniu** – de exemplu:
   - **Zoho Mail** (plan gratuit pentru 1 domeniu)
   - **Google Workspace** (plătit)
   - **Cloudflare Email Routing** (doar primire – nu poți trimite direct)

2. **Configurare DNS** la ROTLD (portal.rotld.ro) – înregistrări MX date de furnizorul de email

3. **În Django/Render** – folosești SMTP-ul furnizorului (ex: Zoho îți dă `smtp.zoho.com`, user, parolă)

---

## Test rapid

După config, trimite o **cerere de adopție** pe site la un animal care are email ONG setat. ONG-ul ar trebui să primească emailul cu linkul de validare.

---

## Dacă nu merge

- **Gmail**: Verifică că ai folosit **Parolă pentru aplicație**, nu parola de cont
- **Render**: Verifică în **Logs** dacă apare eroare la trimitere
- **Fără config**: Dacă nu pui `EMAIL_HOST`, Django afișează emailurile în consolă (local) – nu le trimite real
