# Verificare email reală (SMTP) — EU-Adopt

## 1. Ce trebuie în `.env`

| Variabilă | Rol |
|-----------|-----|
| **`EMAIL_HOST_PASSWORD`** | **Obligatoriu** pentru trimitere reală: parola de **aplicație** Google (nu parola contului). Fără ea, Django folosește **consola** — nu ajunge nimic în Gmail/Yahoo. |
| `EMAIL_HOST_USER` | Opțional. Implicit `euadopt@gmail.com`. Setează dacă trimiți din alt cont Gmail configurat la fel. |
| `DEFAULT_FROM_EMAIL` | Opțional. Implicit = `EMAIL_HOST_USER`. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS` | Opțional. Implicit Gmail `smtp.gmail.com:587` + TLS. |
| `EUADOPT_SITE_BASE_URL` sau `EUADOPT_SITE_BASE_URL_DEV` | Linkuri **absolute** în mailuri (reset parolă, confirmare email, adopție). Local: `EUADOPT_SITE_BASE_URL_DEV=http://127.0.0.1:8000`. |
| `EUADOPT_RELAX_EMAIL_UNIQUE=1` | Doar dev/QA: permite același email pe **mai multe conturi** (ex. inbox comun). **Șterge** după teste. |

După modificări: **repornește** serverul Django ca să reîncarce `.env`.

## 2. Probă rapidă fără flux UI

Din rădăcina proiectului:

```bash
python manage.py euadopt_mail_probe
python manage.py euadopt_mail_probe --usernames dpf,dg1,dm,rares
python manage.py euadopt_mail_probe --to rarespepsi@gmail.com
python manage.py euadopt_mail_probe --dry-run
```

- Comanda afișează `EMAIL_BACKEND`. Dacă vezi `console`, lipsește `EMAIL_HOST_PASSWORD`.
- Subiectele folosesc prefixul `[username]` și un **run=** timestamp (vezi `home/mail_helpers.py` + comanda) — util când **mai multe conturi** au același inbox și ca Gmail să nu le strângă într-un singur fir greșit.

## 3. Conturi „funcționale” pentru mail

- **`is_active=True`** — altfel login-ul e blocat (Admin → Users).
- **`User.email`** — trebuie să fie adresa unde verifici **primirea** (inclusiv folder **Spam**).
- Fluxuri utile de verificare end-to-end:
  - **Reset parolă** — `/login/forgot-password/` (trimite link).
  - **Edit cont → schimbare email** — dacă schimbi emailul, vine mesaj de confirmare cu link.
  - **Adopție / transport** — după ce ai date de test, mailurile din `home/views.py` / `home/transport_dispatch.py` folosesc deja `email_subject_for_user` unde e cazul.

## 4. Primire (inbox)

- Trimite către o adresă la care ai acces (ex. Gmail).
- Verifică **Spam / Promoții** pentru mesaje de la `DEFAULT_FROM_EMAIL`.
- Dacă folosești **același inbox** pentru `dpf`, `dg1`, `dm`: diferențiază mesajele după **`[username]`** în subiect.

## 5. Producție

- Nu lăsa `EUADOPT_RELAX_EMAIL_UNIQUE` activat.
- Folosește `DJANGO_SECRET_KEY`, `EMAIL_HOST_PASSWORD` și `EUADOPT_SITE_BASE_URL` doar în variabile de mediu securizate (nu în git).
