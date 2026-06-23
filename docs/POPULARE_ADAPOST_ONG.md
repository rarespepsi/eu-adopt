# Populare adăposturi & ONG — procedură și comutare la lansare

**Ultima actualizare:** 2026-06-02  
**Scop:** reguli **globale** (env + cod) pentru faza de populare; fără excepții per organizație.  
**Nu include:** cereri adopție, mesaje adopție, Transport din flux adopție.

---

## 1. Cine intră în procedură

| Tip | CSV / Add USER | Signup | Rol după cont |
|-----|----------------|--------|----------------|
| Adăpost | `tip_cont = adapost` | `/signup/organizatie/` | `ROLE_ORG` |
| ONG / asociație | `tip_cont = org` | `/signup/organizatie/` | `ROLE_ORG` |

Aceleași reguli de populare pentru ambele. Diferă doar șablonul email invitație (`adapost` vs `ong`).

---

## 2. Faza POPULARE — reguli active

### 2.1 Mediu (`.env`)

| Variabilă | Valoare populare |
|-----------|------------------|
| `EUADOPT_PRELAUNCH_MODE` | `1` |
| `EUADOPT_POPULATION_ONBOARDING` | `1` (implicit `1` când prelaunch) |
| `EUADOPT_SMS_OTP_ENABLED` | `0` |
| `EUADOPT_SMS_OTP_DEV_CODE` | cod fix 6 cifre (ex. `528419`) — **același pentru toți** |
| `EUADOPT_SITE_BASE_URL` | HTTPS domeniu final |
| `EUADOPT_STAFF_INVITE_EMAIL_ENABLED` | `0` la simulare, apoi `1` la pilot |
| SMTP Zoho | complet |
| `SITE_PUBLIC` | `1` |

### 2.2 Produs (cod)

| Regulă | Detaliu |
|--------|---------|
| SMS | Ecran păstrat; cod afișat pe pagină (fără text „pentru test”) |
| Animale ONG | Min **2**, max **5** (toate speciile, `is_published=True`) |
| Meniu ONG | Redus: Acasă, Prietenul tău, MyPet, Contact, Cont — fără Shop, Transport, Servicii, I Love |
| Banner | Sub navbar: progres populare (ex. „1/2 animale minime”) |
| Invitații | Add USER — valuri, max 30/zi, cooldown 14 zile |

### 2.3 Acces permis (populare)

**Fază inițială** (`EUADOPT_POPULATION_SUPERUSER_ONLY=1`): doar **superuser** (administrator) — login + panou staff; fără login ORG, fără signup organizație.

**După deschidere invitații** (`EUADOPT_POPULATION_SUPERUSER_ONLY=0`):

- **Adăposturi** și **ONG-uri** (`ROLE_ORG` — același rol tehnic)
- Signup ONG + SMS + activare email  
- **MyPet** (add/edit animale)  
- **Prietenul tău** + fișă animal  
- **Contact**, **Cont**

### 2.4 Nu e în scope populare

Shop, Transport, I Love, cereri adopție, promovare plătită, magazin colaborator.

### 2.5 Procedură operațională staff

1. Import CSV — email real, `tip_cont` adapost/org  
2. Simulare invitații (`EUADOPT_STAFF_INVITE_EMAIL_ENABLED=0`)  
3. Pilot 5–10 organizații / 1 județ  
4. Valuri ~20/zi (max 30/zi)  
5. Poll inbox; respect „nu contacta”  
6. Succes = cont creat + ≥2 animale publicate  

---

## 3. La LANSARE — checklist comutare

| # | Acțiune |
|---|---------|
| L1 | `EUADOPT_PRELAUNCH_MODE=0` |
| L2 | `EUADOPT_POPULATION_ONBOARDING=0` |
| L3 | `EUADOPT_SMS_OTP_ENABLED=1` + `EUADOPT_SMSAPI_TOKEN` |
| L4 | Meniu complet (sau pe rol) |
| L5 | Invitații continuă sau signup public ONG |

**Cod:** `home/population_onboarding.py`, `EUADOPT_POPULATION_ONBOARDING` în settings.

---

## 4. Principiu

> Orice regulă = flag global sau setare în cod — **nu** excepții manuale per adăpost.

---

## 5. Decizii înregistrate

- Ecran SMS: **păstrat**  
- Cod SMS: **unul pentru toți** până la SMSAPI  
- Min/max animale: **2–5**, toate speciile, doar `ROLE_ORG`  
- Meniu: **redus** în populare (nu doar MyPet)  
- Adopții: **după** populare (procedură separată)
