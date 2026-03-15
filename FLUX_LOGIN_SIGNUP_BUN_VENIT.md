# Flux: Login, Creează cont, Notă bun venit

Documentație scurtă a legăturilor dintre paginile de autentificare și înregistrare, fără dubluri sau reguli contradictorii.

---

## 1. Buton Login / Intră

- **URL:** `/login/` → `login_view`
- **Template:** `anunturi/login.html`
- **POST:** email sau username + parolă → `authenticate` + `login` → redirect la `next` sau `/`
- **Link „Creează cont”:** → `signup_choose_type` (alegere tip: PF / ONG / Colaborator)

---

## 2. Creează cont – Alegere tip

- **URL:** `/signup/alege-tip/` → `signup_choose_type_view`
- **Template:** `anunturi/signup_choose_type.html`
- **Linkuri:**
  - Persoană fizică → `signup_pf`
  - Adăpost / ONG → `signup_organizatie`
  - Colaborator → `signup_colaborator`
- **Parametri GET (de la link activare invalid/expirat):** `link_invalid=1`, `link_expirat=1` → mesaje în pagină

---

## 3. Formulare înregistrare (PF / ONG / Colaborator)

| Tip        | URL                          | View                     | La submit (POST valid)     |
|-----------|------------------------------|--------------------------|----------------------------|
| PF        | `/signup/persoana-fizica/`   | `signup_pf_view`         | `signup_pending` în sesiune → **signup_verificare_sms** |
| ONG       | `/signup/organizatie/`       | `signup_organizatie_view`| `signup_pending` (role=org) → **signup_verificare_sms** |
| Colaborator | `/signup/colaborator/`     | `signup_colaborator_view`| `signup_pending` (role=collaborator) → **signup_verificare_sms** |

- La erori validare: re-render formular cu `form_prefill` și mesaje eroare (telefon/email deja folosit nu șterg `signup_pending` la redirect din SMS).
- **Un singur flux comun:** toți cei trei tipuri merg la același pas SMS.

---

## 4. Verificare SMS (comun)

- **URL principal:** `/signup/verificare-sms/` → `signup_verificare_sms_view`
- **URL alias (compatibilitate):** `/signup/persoana-fizica/sms/` → `signup_pf_sms_view` (apelează același view)
- **Template:** `anunturi/signup_pf_sms.html` (form POST la `signup_verificare_sms`)
- **GET:** afișează formular cod SMS, contor 5 min, „Retrimite cod” (max 3, apoi cooldown 45 min).
- **POST cod corect (111111):**
  - Verificare telefon/email nu deja folosit (altfel redirect la formularul de tip cu `?phone_taken=1` / `?email_taken=1`, **fără** ștergere `signup_pending`).
  - Creare user `is_active=False`, AccountProfile + UserProfile (PF/ORG/COLLAB).
  - Trimitere email cu link activare (TimestampSigner, 5 min).
  - Ștergere `signup_pending` din sesiune, setare `signup_waiting_id`, `signup_waiting_user_pk`, `signup_email_resend_count`, `signup_link_created_at`.
  - **Redirect mereu** la **signup_pf_check_email** („Verifică email”), nu la home.

---

## 5. Verifică email

- **URL:** `/signup/verificare-email/` → `signup_pf_check_email_view` (nume view: check email, nu doar PF).
- **Template:** `anunturi/signup_pf_check_email.html`
- Conține contor 5 min pentru link, „Retrimite link” (max 3, cooldown 45 min), polling pentru activare pe alt device.
- **Retrimite link:** POST la `signup_retrimite_email` → redirect înapoi cu `?retrimis=1` sau `?cooldown=1`.

---

## 6. Activare cont (link din email)

- **URL:** `/signup/verify-email/?token=...&waiting_id=...` → `signup_verify_email_view`
- Verificare token (TimestampSigner, max_age=300). La expirat/invalid → redirect `signup_choose_type?link_expirat=1` sau `?link_invalid=1`.
- La succes: `user.is_active = True`, `auth_login(request, user)`, curățare chei sesiune (`signup_waiting_id`, `signup_waiting_user_pk`, resend/cooldown).
- Dacă există `waiting_id`: se pune în cache `one_time_token` pentru tab-ul „Verifică email” (activare pe alt device).
- **Răspuns:** render `signup_activated.html` → mesaj „Cont activat”, redirect după 2 s la **home?welcome=1**.

---

## 7. Login pe alt device (după activare)

- Pagina „Verifică email” face polling la `signup_check_activation_status?waiting_id=...`. Când activarea s-a făcut (pe telefon), primește `one_time_token`.
- Redirect la **signup_complete_login?token=...** → `signup_complete_login_view`: logare cu token, curățare sesiune, redirect **home?welcome=1**.

---

## 8. Nota „Bine ai venit” pe Home

- **URL:** `/` (home) cu **`?welcome=1`** (sau legacy `?welcome_demo=1`).
- **View:** `home_view` → `show_welcome_demo = True` dacă `welcome=1` sau `welcome_demo=1`.
- **Template:** `anunturi/home_v2.html` → overlay „Bine ai venit în EU-Adopt” când `show_welcome_demo` este True.

**Surse pentru welcome=1:**
1. După activare pe același device: `signup_activated.html` redirecționează la `home?welcome=1`.
2. După activare pe alt device: `signup_complete_login_view` redirecționează la `home?welcome=1`.

---

## Reguli unice (fără dubluri)

- Un singur pas SMS pentru toți: **signup_verificare_sms**; URL alias `signup_persoana-fizica/sms` doar redirecționează același view.
- După SMS reușit se merge **mereu** la **signup_pf_check_email**, niciodată direct la home.
- Mesajul de bun venit se arată **doar** când utilizatorul ajunge la home cu `?welcome=1` (sau `welcome_demo=1`).
- Sesiune: după activare (verify-email) se curăță toate cheile `signup_*` relevante; la complete-login se curăță din nou pentru device-ul care face login cu token.
- La telefon/email deja folosit (din SMS) se face redirect la formularul de tip **fără** ștergerea `signup_pending`, astfel că datele (inclusiv parola) rămân pentru refill.
