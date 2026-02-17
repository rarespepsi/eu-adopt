# Acces doar tu când site-ul e „în pregătire”

Când `SITE_PUBLIC = False`, doar tu poți vedea site-ul de pe laptop (restul văd „Site în pregătire”).

## Pași

1. **Setează un cod secret** (doar tu să îl știi), de ex. un cuvânt lung:  
   `Ma1nt3nanc3-2025` sau orice altceva greu de ghicit.

2. **În `.env`** (sau pe Render la Environment Variables) adaugă:
   ```bash
   MAINTENANCE_SECRET=Ma1nt3nanc3-2025
   ```
   (folosește codul tău, nu neapărat acest exemplu.)

3. **Pe laptop**, deschide o singură dată în browser:
   ```
   https://siteul-tau.ro/acces-pregatire/Ma1nt3nanc3-2025/
   ```
   (înlocuiește `siteul-tau.ro` cu domeniul tău și `Ma1nt3nanc3-2025` cu codul din `.env`.)

4. După ce intri pe acel link, se setează un **cookie** în browser. De atunci, **doar pe acel laptop** (acel browser) vei vedea site-ul normal. Toți ceilalți vizitatori vor vedea „Site în pregătire”.

- Cookie-ul e valabil **30 de zile**. După expirare, deschizi din nou link-ul secret pe laptop.
- **Nu partaja** link-ul (conține codul secret). Dacă vrei să vezi site-ul și de pe telefon, poți folosi același link acolo (se va seta cookie și pe telefon).

## Local (pe calculator)

În `.env` din rădăcina proiectului:
```bash
SITE_PUBLIC=False
MAINTENANCE_SECRET=Ma1nt3nanc3-2025
```

Apoi deschide: `http://127.0.0.1:8000/acces-pregatire/Ma1nt3nanc3-2025/`

## Când ești gata să lansezi

Setează `SITE_PUBLIC=True` (sau 1 / yes) în mediu. Atunci toată lumea vede site-ul și link-ul secret nu mai e necesar.
