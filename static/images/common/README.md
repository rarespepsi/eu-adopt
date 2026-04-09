# Imagini – comune / reutilizabile

## `backgrounds/`

Texturi subtile, pattern-uri discrete, fallback-uri sau poze folosite în **mai multe** zone (nu legate strict de login/signup).

**Static:** `{% static 'images/common/backgrounds/nume-fisier.ext' %}`

## Când folosești `common/` vs foldere dedicate

- **O pagină clară** (login, signup) → folderul ei (`login/`, `signup/`).
- **Același fișier în 2+ contexte** sau „atmosferă generică” → `common/backgrounds/`.
