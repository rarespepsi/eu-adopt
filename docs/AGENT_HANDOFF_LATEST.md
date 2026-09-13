---
# Handoff agent — ultima pauză
**Data/ora (RO):** 2026-09-13 13:01
**Sursă:** telefon · Cloud Agent · eu-adopt / main
**User:** pauză; continuă de pe laptopul de la birou

## Ce s-a făcut
- Publicată campania **Leu, Dolj, 14.09.2026** (câini + pisici), afiș din postarea FB, link `https://www.facebook.com/share/p/1DPsATLxmx/`
- LIVE: `https://eu-adopt.ro/publicitate/campanii/dolj/` · pk=88 · user `IoanaSerbacov` (17)
- Facebook auto RO: postat `970069896196143_122126618421268143` · permalink `https://www.facebook.com/122123177715268143/posts/122126618421268143`
- DE/FR/ES/COM: plafon zilnic — rămân pending
- Discutat urmărire grupuri FB (fără implementare, fără scraper, fără contul Ioanei)
- Comandă Playwright pe facebook.com: **respinsă ca abordare** (zid login, ToS, URL-uri placeholder)

## Fișiere atinse
- `docs/AGENT_HANDOFF_LATEST.md` — acest handoff
- **Cod site:** nimic în sesiunea asta (doar date live: CampanieSterilizare pk=88 + media pe H)

## Git
- Branch: main
- Commit(uri): handoff campanii sterilizare 13 sep (acest fișier)
- Push: da (doar docs; **fără deploy**)

## Deploy Hetzner
- nu · live SHA rămâne `c45bff7` · campania Leu e **doar în DB/media pe H**, nu în git

## Pentru agent laptop (caută aici)
- git log -3 --oneline
- citește `docs/AGENT_HANDOFF_LATEST.md`
- test: https://eu-adopt.ro/publicitate/campanii/dolj/ (Leu 14.09)
- zone înghețate: orice edit site = `1977` + OK

## Următorul pas
- Nu rula scraper Facebook anonim / Playwright pe facebook.com
- Flux agreat: Google pe **județele goale** (știri, smeura.com) + tu trimiți link+afiș din grupul Ioanei
- Dedup: Leu unic; cardurile identice de deasupra pe Dolj = **Călărași (comuna Dolj)**, luni diferite, același afiș
- Neînceput: Ilfov pisici Mogoșoaia/Jilava/Domnești; rest Smeura sep 2026; Oinacu (dată neconfirmată)
- Grup principal: `https://www.facebook.com/groups/448262345586820/` (Anunturi Campanii Sterilizari). Token pagina EU-Adopt **nu** citește grupuri. Fără login Ioana.
---
