# Publicitate - email "detalii postare/comanda" dupa plata

## Scop

Dupa ce o comanda `PublicitateOrder` devine **platita** si se aplica programarea liniilor (`_apply_publicitate_paid_order`), cumparatorul primeste un email **separat** fata de cel pentru **materiale creative** (formular cu token).

- **Creative:** `_send_publicitate_creative_email` - link formular, coduri scurte; `PublicitateOrderCreativeAccess.email_sent_at`.
- **Contract/postare:** `_publicitate_send_contract_posting_email_if_needed` - rezumat complet comanda + linii (perioade, preturi, cod validare, nota scurta); idempotent prin `PublicitateOrder.contract_posting_email_sent_at`.

## Cand se trimite

- La finalul lui `_apply_publicitate_paid_order`, prin `transaction.on_commit(...)` (dupa commit DB, nu inainte).
- La reconfirmare demo pe comanda deja `paid`: `transaction.on_commit` in `publicitate_checkout_demo_confirm_view` (fara reapelare `_apply`), pentru recuperarea trimiterii daca lipsea.

## Destinatar si continut

- Destinatar: `order.user.email`.
- Fara adresa: warning in log, **nu** se seteaza `contract_posting_email_sent_at` (retry ulterior prin rulare flow sau job dedicat).
- Header SMTP: `X-EUAdopt-Mail: publicitate_contract_posting` (via `send_mail_text_and_html`).

## Idempotenta

- Daca `contract_posting_email_sent_at` este setat, mailul nu se retrimite.
- Dupa `send_mail` reusit: update atomic pe `PublicitateOrder` doar daca campul era inca `NULL`.

## De ce in docs (versionat)

Regula initiala a fost pusa in `.cursor/rules/`, dar folderul `.cursor/` este ignorat in Git.  
Varianta stabila pentru proiect este aceasta documentatie in `docs/`, astfel incat regula sa existe in repository pentru toata echipa.
