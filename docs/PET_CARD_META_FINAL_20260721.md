# Carduri animale — localitate · M/F · vârstă (FINAL)

**Data:** 2026-07-21  
**Confirmat:** utilizator — I Love pe același rând cu localitatea, apoi „perfect”.  
**Live Hetzner:** `6a219b0` (după `2f45224`, `d88fef1`)  
**Regulă Cursor:** `.cursor/rules/PET_CARD_META_MEMORAT.mdc`

---

## Ce vede utilizatorul

Sub **numele** animalului (sau sub bara cu ♥ / nume pe PT):

```text
București · M · 2 ani
```

- **Localitate:** `city` din fișă; fallback `county`
- **Sex:** `m` → **M**, `f` → **F**
- **Vârstă:** câmpul **Vârstă aproximativă** din MyPet (`age_label`)

Lipsă câmp → segment omis. Rândul întreg lipsește dacă nu există nici localitate, nici sex, nici vârstă.

---

## Pagini acoperite

| Zonă | URL / context |
|------|----------------|
| Prietenul tău | `/pets/` grilă P2 + `p2-more` |
| Fișă adăpost | `/adaposturi/…` grilă câini |
| I Love | `/i-love/` |
| Acasă | A2 doar card **full** (nu compact cu citat promo) |

---

## Fișiere de restaurat

1. `home/pet_card_display.py`
2. `home/templatetags/anunturi_extras.py` — tag `pet_card_meta_footer`
3. `templates/anunturi/includes/pet_card_meta_footer.html`
4. `static/css/pet-card-meta.css` — cache **`?v=2`** în `templates/base.html`
5. `home/pt_p2_list.py` — câmpuri `sex`, `oras`, `varsta` pe dict P2
6. `home/views.py` — I Love + HOME A2 dict
7. `templates/anunturi/includes/pt_p2_card.html` — `.pt-p2-card-bottom-stack`
8. `static/css/pt-v2.css` — stack jos; `pt.html` → `pt-v2.css?v=pt385-pet-card-meta`

---

## Commit-uri (ordine)

| SHA | Mesaj |
|-----|--------|
| `2f45224` | feat: meta localitate + M/F + vârstă |
| `d88fef1` | cache bust PT pt-v2 |
| `6a219b0` | fix: același rând localitate + M/F + vârstă |

---

## Înghețare

Orice schimbare layout / text / ordine → parolă **`1977`** + **OK explicit** în același mesaj.
