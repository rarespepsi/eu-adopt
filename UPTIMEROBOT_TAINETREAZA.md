# Ține site-ul treaz (fără „somn” pe Render)

Pe **planul Free** al Render, serviciul se oprește după ~15 min fără trafic. La primul acces după aceea se „trezește” în 30 sec – 2 min (cold start).

**Soluție gratuită:** **UptimeRobot** – un monitor care face un request la site la fiecare 5 minute. Render consideră că există trafic → **nu pune aplicația la somn** → paginile se încarcă rapid.

---

## Pași (o singură dată)

1. Mergi la **https://uptimerobot.com** și creează cont gratuit (sau loghează-te).

2. Click **+ Add New Monitor**.

3. Completează:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** `EU Adopt – health` (sau cum vrei)
   - **URL (or IP):** `https://eu-adopt.onrender.com/health/`
   - **Monitoring Interval:** 5 minutes (sau cel mai mic permis pe planul free, ex. 5 min)

4. Click **Create Monitor**.

Gata. UptimeRobot va accesa `/health/` la fiecare 5 min → Render ține serviciul pornit → site-ul nu mai „doarme”.

---

## De ce `/health/`?

- E un endpoint ușor (răspunde rapid, fără pagini grele).
- E în lista de path-uri permise și când site-ul e „în pregătire” (maintenance), deci monitorul nu primește 503.
- Un singur monitor pe acest URL e suficient; tot serviciul Render rămâne treaz (inclusiv eu-adopt.ro / eu-adopt.com dacă sunt pe același Web Service).

---

## Linkuri rapide

| Ce | Link |
|----|------|
| UptimeRobot | https://uptimerobot.com |
| Health check (test manual) | https://eu-adopt.onrender.com/health/ |

După ce monitorul rulează 5–10 minute, deschide din nou **eu-adopt.com** sau **eu-adopt.onrender.com** – ar trebui să se încarce fără cold start.
