# User „doar campanii sterilizare” — discuție memorată

**Data:** 2026-08-08  
**Stare:** discuție internă agreată ca **direcție**; userul final încă **nu** a confirmat (se anunță când e gata).  
**Nu implementat încă** — așteaptă anunț + `1977` + OK.

---

## Context

Un partener vrea **doar publicitate / postare campanii de sterilizare**.  
Nu are timp pentru adopții, MyPet, shop etc.  
Ai cerut de la el **doar adresa de email**.

---

## Decizie de produs (propusă / agreată în discuție)

| Punct | Decizie |
|-------|---------|
| Tip cont | **PF** (nu ONG, nu colaborator) |
| Personalizare | După **adresa de email** (whitelist), nu tip cont nou |
| După login | Deschide **direct** pagina de încărcare campanii: `/account/?campanie=1` |
| Postări | **Nelimitate** (campaniile sterilizare deja nu au plafon ca animalele PF) |
| Signup / login | Aceiași pași ca PF, cu excepție telefon |
| Telefon | **Nu** obligatoriu SMS. Dacă **nu** introduce număr → fără verificare SMS (activare pe email). Dacă **introduce** număr → **verificare SMS** ca la PF |

---

## Ce există deja în cod (nu inventăm de la zero)

- Model `CampanieSterilizare` + postare din Cont (`form_type=campanie_sterilizare`)
- Hartă publică: `/publicitate/campanii/` (+ județ)
- Login: redirect la `next` sau `/` — **fără** landing per-email încă
- PF: SMS + email în fluxul normal — de adaptat pentru whitelist

---

## Implementare țintă (când se dă OK)

1. Whitelist emailuri „campanii only” (preferabil: tabel staff / admin, sau setare pe H; de confirmat la implementare).
2. La **login**: dacă emailul e pe listă → redirect `/account/?campanie=1` (ignoră Home default; respectă `?next=` dacă e setat explicit, sau nu — de decis la implementare).
3. La **signup PF**: dacă emailul e pe listă → telefon opțional; fără telefon = skip SMS; cu telefon = OTP.
4. Opțional ulterior: meniu redus (doar campanii + cont + logout) — **nu** e obligatoriu în primul pas.

---

## Variante rapide (până la implementare)

Link manual:  
`https://eu-adopt.ro/login/?next=/account/?campanie=1`  
→ după login ajunge la formular campanii, fără cod nou.

---

## De confirmat când revii cu userul

- [ ] Emailul exact (whitelist)
- [ ] Lista: admin staff vs `.env` pe H
- [ ] Meniu redus acum sau doar landing după login
- [ ] Userul final a acceptat: PF + email + campanii nelimitate + telefon opțional

---

## Comandă de implementare (când e momentul)

Ex.: `1977 ok, implementează PF campanii pe email (whitelist + landing + telefon opțional)`

---

## Legături

- Hartă campanii: `home/campanii_ro.py`, `publicitate_campanii_*`
- Model: `home.models.CampanieSterilizare`
- Postare: Cont / `form_type=campanie_sterilizare` în `home/views.py`
