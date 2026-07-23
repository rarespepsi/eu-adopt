# EU-Adopt — decizii produs (site-uri fără `.ro`)

**Memorat:** 2026-07-23 · **Savepoint git înainte de implementare meniu/publi EU:** vezi commit `docs: memorize EU product decisions` / SHA pe `main` după push.

**`.ro` (eu-adopt.ro):** înghețat total ca layout/produs RO — nu se modifică fără `1977` + OK. Publicitate pe `.ro` = clienți RO (plătit), neschimbat ca principiu.

---

## Domenii

| Host | Rol |
|------|-----|
| `eu-adopt.ro` | Site RO complet |
| `euadopt.com` | Hub EU — limba start **EN**; selector toate limbile UE |
| `euadopt.de` / `.fr` / `.es` | Același catalog; default DE/FR/ES |
| `.eu` / `.org` / cratimă | 301 → `.com` |

O app, o DB. Animale din RO. Coming soon public pe non-`.ro` până la **lansarea full `.ro`** (`EUADOPT_NON_RO_STAFF_ONLY=1`).

---

## Meniu EU (țintă)

**Vizibile:** Home · Find a friend (PT) · **Transport** (flux normal + sponsorizare autocar) · MyPet · I Love · Intră · limbi · Terms · Contact  

**Ascunse pe EU:** Servicii · Shop · **Adăpost/ONG** · Coș / Magazinul meu / Reclama în meniul public  

**De ce fără Adăpost/ONG pe EU:** detalii adăpost pe domenii externe = risc (expunere). Doar pe `.ro`.

**Home pe EU:** același ca pe RO (layout).

---

## Publicitate / Reclama

1. Superuser intră în **Reclama pe `.ro`**.
2. Filtru: **Publi RO** | **Publi EU** (`?market=ro|eu`).
3. Postezi pe piața EU → `ReclamaSlotNote.market=eu` → apare pe `.com` și se **oglindă** pe `.de`/`.fr`/`.es` (**fără** `.ro`).
4. Pe `.ro` rămâne reclama **plătită** (scrie mereu `market=ro`).
5. **Click** pe EU: link către `eu-adopt.ro/...` e localizat la path pe domeniul curent.
6. **Text** casetă: câmp opțional `alt_i18n` / `i18n` în JSON → limba activă.
7. Sloturi EU: Admin → Notițe Reclama (`market=eu`) sau Burtieră în Reclama cu Publi EU; UI upload dedicat sloturi = următorul rafinament.
8. Lista exactă de pagini/sloturi publi pe EU = **la final**.

**Cod:** `home/pub_markets.py`, `home/pub_slot_defaults.py`, migrare `0076_reclamaslotnote_market`.

---

## Traduceri UI

- Navbar: deja dicționar 24 limbi (`home/eu_nav_labels.py`).
- Corp pagini (PT, Transport, etc.): etapizat — EN întâi, apoi restul.
- Descrieri animale: **mai târziu** (cerere explicită).

---

## Ordine implementare (agreată)

1. ~~Meniu EU (+Transport, −Adăpost/ONG)~~ — făcut
2. ~~Memorare~~ — `docs/EUADOPT_EU_PRODUCT_DECISIONS.md`
3. Reclama filtru RO/EU + oglindă pe domenii EU
4. Click pe domeniul curent + text = limba activă
5. Traduceri UI pe paginile EU
6. Sloturi/pagini publi EU — listă finală
7. Scoate Coming soon — **după** lansare full `.ro`

**Savepoint pre-produs:** `525d77a` (docs) · cod flags `ed19a1b`

---

## Rollback

- Git: `git log` / checkout SHA savepoint de dinaintea pașilor de produs.
- ZIP local: `Desktop\EU-Adopt-backups\good-releases\`
- Procedură: `BACKUP_DEPLOY_PROCEDURA.mdc` / `docs/BACKUP_ROLLBACK.md`
