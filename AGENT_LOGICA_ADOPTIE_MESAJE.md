# Logică adopție + mesaje (EU-Adopt) – notă pentru agenți

## Scop

- **PF** apasă **VREAU SA-L ADOPT** pe fișă → se creează `AdoptionRequest` + mesaj **fără date personale structurate**; owner e notificat în **MyPet → Mesaje**.
- **Nu** se afișează / nu se trimit prin email datele adopatorului către owner **până** când owner apasă **Acceptă adopția**.
- La **Accept**: email **owner** = date adoptator; email **adopter** = date owner/ONG (din `User` + `UserProfile` + `AccountProfile.role`).
- După accept: mesaje **libere** în fișă / inbox (adopter poate folosi câmpul MESAJE și reply în conversație).
- **MyPet**: coloana **În curs** arată „Așteptare (N)” / „Adopție acceptată”; buton **Adopție finalizată** (doar owner) după accept → `UserAdoption` completed, anunț `is_published=False`.

## Model

- `home.models.AdoptionRequest`
  - `animal` → `AnimalListing`
  - `adopter` → `User`
  - `status`: `in_asteptare` | `acceptata` | `respinsa` | `finalizata`
  - `accepted_at` (setat la accept)

## Endpoint-uri

| Metodă | URL | Rol |
|--------|-----|-----|
| POST | `/pets/<pk>/adopt/request/` | PF: creează cererea + mesaj template (`pet_adoption_request_view`) |
| POST | `/pets/<pk>/message/` | Mesaj liber din fișă **doar** dacă există cerere `acceptata` pentru acel user + animal |
| POST | `/mypet/messages/adopter/<pk>/reply/` | Idem: doar după accept |
| GET | `/mypet/messages/<pet_pk>/<sender_id>/` | Thread owner; include JSON `adoption_request` pentru butoane Accept/Respinge |
| POST | `/mypet/adoption/<req_id>/accept/` | Owner: accept + emailuri + mesaj sistem către adopter |
| POST | `/mypet/adoption/<req_id>/reject/` | Owner: respinge + mesaj scurt către adopter |
| POST | `/mypet/adoption/<req_id>/finalize/` | Owner: finalizează; `UserAdoption` completed; scoate anunțul |

## Reguli de business

1. **O singură cerere „deschisă”** per (animal, adopter): dacă ultima cerere e `in_asteptare` sau `acceptata`, nu se retrimite; după `respinsa` poate reîncerca.
2. La **accept**: toate celelalte cereri `in_asteptare` pentru **același animal** trec în `respinsa` (fără mesaj suplimentar automat către acei useri – doar update DB).
3. Nu se acceptă o cerere nouă dacă există deja o cerere `acceptata` pentru acel animal (trebuie finalizată sau rezolvată manual).
4. **Email**: `home.views._send_adoption_accept_emails` – folosește `DEFAULT_FROM_EMAIL`; erorile se loghează, nu blochează neapărat salvarea (accept deja salvat înainte de trimitere).
5. **Finalize** mută status la `finalizata`, creează/actualizează `UserAdoption` (`status=completed`, `source=mypet_adoption_flow`), pune `AnimalListing.is_published=False`.

## UI

- **pets-single.html**: mesajele libere + Send doar dacă `adopter_messaging_unlocked`; altfel textarea explicativ dezactivat; buton roșu adopt cu `fetch` POST + CSRF.
- **mypet.html**: thread owner randă bar **Acceptă / Respinge** dacă `adoption_request.status == in_asteptare`; rândul din tabel cu etichetă + buton finalizare.

## Edge cases

- Conturi fără `can_adopt_animals` nu pot trimite cerere (ex. colaborator-only dacă e setat astfel).
- **Colaborator** cu `can_adopt_animals` false: blocat la cerere.
- Mesajele vechi trimise **înainte** de această regulă pot conține PII; după deploy, mesajele noi de la adopter sunt blocate până la accept.

## Fișiere cheie

- `home/models.py` – `AdoptionRequest`
- `home/views.py` – cereri, emailuri, `_adopter_messaging_allowed`, `mypet_view` (coloana În curs)
- `home/urls.py` – rute adopție
- `templates/anunturi/pets-single.html`, `templates/anunturi/mypet.html`
