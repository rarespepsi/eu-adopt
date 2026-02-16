# Cloudflare pentru eu-adopt.ro – pas cu pas

DNS gratuit în loc de 5.99 EUR/an la registrar.

---

## Partea 1: Cont Cloudflare

### Pasul 1
Deschide în browser: **https://dash.cloudflare.com/sign-up**

### Pasul 2
Înscrie-te cu:
- Email (orice adresă)
- Parolă
- Apasă **Create Account**

### Pasul 3
Verifică emailul și apasă pe linkul de confirmare (dacă apare).

---

## Partea 2: Adaugă domeniul

### Pasul 4
După login, ar trebui să vezi „Add a site” sau „Add your first domain”.

Apasă pe **Add a site** (sau **Add site**).

### Pasul 5
La „Enter your site”, scrie: **eu-adopt.ro**

Apasă **Add site**.

### Pasul 6
La „Select a plan” alege **Free** (planul gratuit).

Apasă **Continue**.

### Pasul 7
Cloudflare va scana domeniul și va arăta înregistrări existente.

Apasă **Continue**.

---

## Partea 3: Nameserveri (importanți)

### Pasul 8
Cloudflare îți dă **2 nameservere**, de exemplu:

- `ada.ns.cloudflare.com`
- `bob.ns.cloudflare.com`

*(La tine vor fi alte nume – Cloudflare le generează.)*

**Notă-le** sau lasă pagina deschisă – îi vei folosi la Pasul 13.

### Pasul 9
Cloudflare îți va spune să mergi la registrarul tău (unde ai cumpărat eu-adopt.ro) și să schimbi nameserverele.

Apasă **Continue** (sau „I’ve updated my nameservers” după ce termini).

---

## Partea 4: DNS în Cloudflare

### Pasul 10
În Cloudflare, mergi la **DNS** → **Records** (meniu stânga).

### Pasul 11 – Prima înregistrare (A)

1. Apasă **Add record**
2. **Type:** A
3. **Name:** @ (sau lasă gol pentru root)
4. **IPv4 address:** 216.24.57.1
5. **Proxy status:** DNS only (nor gri) – nu orange cloud
6. Apasă **Save**

### Pasul 12 – A doua înregistrare (CNAME)

1. Apasă **Add record**
2. **Type:** CNAME
3. **Name:** www
4. **Target:** eu-adopt.onrender.com
5. **Proxy status:** DNS only (nor gri)
6. Apasă **Save**

---

## Partea 5: Schimbă nameserverele la registrar

### Pasul 13
Deschide site-ul unde ai cumpărat domeniul (panoul unde ai văzut CloudDNS).

### Pasul 14
Găsește **eu-adopt.ro** și intră în setări.

### Pasul 15
Caută opțiunea **Nameservers** / **NS** / **Servere de nume**.

### Pasul 16
Schimbă la **Custom nameservers** (sau „I'll use my own nameservers”) și introdu cei 2 nameservere de la Cloudflare:

- Nameserver 1: *(ex. ada.ns.cloudflare.com)*
- Nameserver 2: *(ex. bob.ns.cloudflare.com)*

### Pasul 17
Salvează (Save / Update).

---

## Partea 6: Verificare

### Pasul 18
Propagarea nameserverelor poate dura 15 min – 24 h.

### Pasul 19
În Cloudflare, statusul domeniului va trece din „Pending” în „Active” când totul e corect.

### Pasul 20
În Render, la **Custom Domains**, apasă din nou **Verify** pentru eu-adopt.ro și www.eu-adopt.ro.

---

## Rezumat DNS (pentru Cloudflare)

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | @ | 216.24.57.1 | DNS only |
| CNAME | www | eu-adopt.onrender.com | DNS only |

---

*Proxy „DNS only” (nor gri) = Cloudflare nu face cache pentru început. Poți activa orange cloud mai târziu dacă vrei CDN.*
