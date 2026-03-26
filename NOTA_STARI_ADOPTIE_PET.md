# Notă — stări adopție (câine / cerere)

**Context:** de la momentul în care am stabilizat procedura de adopție în EU-Adopt: stări vizibile pentru animal, stări pentru cereri, coadă de așteptare, termen 7 zile (cu prelungiri limitate), notificări email.

---

## 1. Starea câinelui (`AnimalListing.adoption_state`)

Câmp pe model: `adoption_state` (valori în cod, nu etichete UI).

| Valoare cod        | Sens scurt                          |
|--------------------|-------------------------------------|
| `liber`            | Implicit; fără flux activ de adopție |
| `spre_adoptie`     | Există cerere(e); așteaptă decizie owner |
| `in_curs_adoptie`  | O cerere a fost acceptată; adopție în desfășurare |
| `adoptat`          | Adopție închisă ca finalizată; animal poate rămâne vizibil în PT cu etichetă |

Constante în `home/models.py`: `ADOPTION_STATE_FREE`, `ADOPTION_STATE_OPEN`, `ADOPTION_STATE_IN_PROGRESS`, `ADOPTION_STATE_ADOPTED`.

Sincronizare cu cererile: helper `_sync_animal_adoption_state` în `home/views.py`.

---

## 2. Starea cererii (`AdoptionRequest.status`)

| Valoare cod              | Sens |
|--------------------------|------|
| `in_asteptare`           | Owner nu a acceptat încă (sau e în coadă) |
| `acceptata`              | Owner a acceptat; urmează contact / finalizare |
| `respinsa`               | Respinsă de owner |
| `expirata_neconfirmata`  | Termen acceptare expirat fără finalizare conform regulilor |
| `finalizata`             | Adopție încheiată din flux |

Câmpuri auxiliare cerere: `accepted_at`, `accepted_expires_at`, `extension_count` (max. 2 prelungiri de 7 zile, conform logicii implementate).

---

## 3. Fișiere utile (puncte de intrare)

- **Model:** `home/models.py` — `AnimalListing.adoption_state`, model `AdoptionRequest`.
- **Migrare:** `home/migrations/0033_adoption_states_queue.py` (și evoluții anterioare dacă există).
- **Logică + email:** `home/views.py` — cerere adopție, accept, respingere, finalizare, extend, next, `_sync_animal_adoption_state`.
- **URL-uri:** `home/urls.py` — rute `mypet/adoption/...`, `pet_adoption_request`, etc.
- **UI:** `templates/anunturi/mypet.html`, `pets-single.html`, `includes/pt_p2_card.html` (etichete stare).

---

## 4. Diferență importantă

- **`UserAdoption`** (alt model, istoric/simplu) are stări `pending` / `approved` / `completed` — **nu** este același lucru cu `AdoptionRequest` + `adoption_state` de mai sus. Pentru fluxul „Vreau să-l adopt” din fișă se folosește **`AdoptionRequest`** + **`AnimalListing.adoption_state`**.

---

*Notă de lucru pentru continuitate între sesiuni / agenți noi: citește acest fișier și `home/models.py` pentru valori exacte.*
