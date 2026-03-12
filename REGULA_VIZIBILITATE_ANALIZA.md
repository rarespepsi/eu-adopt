# Regulă: vizibilitate buton „Analiza” în navbar

## Regulă
- **Doar administratorul site-ului** (contul principal) și **cei pe care îi faci tu admini** (useri cu drept de staff/superuser în Django) văd butonul **Analiza** în navbar.
- **Restul utilizatorilor** (PF, ONG, colaboratori obișnuiți) **nu văd** butonul Analiza, nici cu aprobarea ta, decât dacă le acorzi explicit drept de staff (îi creezi ca admini).

## Implementare
- În navbar, butonul „Analiza” este afișat doar dacă `user.is_authenticated` și `user.is_staff`.
- Astfel: utilizatorii obișnuiți nu văd niciodată Analiza; doar tu și eventualii alți staff/superuser creați din Django Admin.
