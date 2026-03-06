# Deploy pe Render – variabile de mediu (producție)

Setări în **Render Dashboard** → serviciul tău → **Environment**:

| Variabilă | Obligatoriu | Exemplu / Notă |
|-----------|-------------|-----------------|
| `SECRET_KEY` | Da | Cheie lungă, aleatorie (generează una nouă pentru producție) |
| `DEBUG` | Da | `False` |
| `ALLOWED_HOSTS` | Recomandat | `domeniu.ro,.onrender.com` (domeniul tău + Render) |
| `SITE_PUBLIC` | Opțional | `True` când site-ul e gata pentru public |
| `CSRF_TRUSTED_ORIGINS` | Da (HTTPS) | `https://domeniu.ro,https://*.onrender.com` |
| `DATABASE_URL` | Da (dacă folosești DB extern) | Setat automat de Render dacă ai adăugat PostgreSQL |
| `MAINTENANCE_SECRET` | Opțional | Cuvânt secret pentru `/acces-pregatire/...` când site în pregătire |

După deploy: SSL redirect, cookie secure și protecții XSS/clickjack sunt active când `DEBUG=False`.
