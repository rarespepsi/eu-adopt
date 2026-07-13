# Facebook / campanii — formular scurt `/inscriere/`

## Link public

- **Producție:** https://eu-adopt.ro/inscriere/
- Alternativ: `https://www.eu-adopt.ro/inscriere/` (același site)

Folosește acest link în postări Facebook, Instagram bio, TikTok etc.

## Flux utilizator

1. Utilizatorul completează formularul scurt: categorie, email, telefon, contact, GDPR.
2. Apasă **„Spre formular cont nou”**.
3. Este redirecționat la formularul lung de înregistrare (adăpost/ONG, colaborator sau PF) cu `?inv=` și câmpuri precompletate.
4. Continuă fluxul existent: formular lung → SMS → cont inactiv → email activare.

**Nu** merge la pagina de login — merge direct la **signup**.

## Compatibilitate Add USER (val SMTP)

Formularul `/inscriere/` **nu blochează** trimiterea de invitații din **Add USER**:

| Câmp / stare | După `/inscriere/` | După val SMTP Add USER |
|------------|-------------------|------------------------|
| `invite_email_last_sent_at` | rămâne gol | se setează |
| `invite_mail_status` | `invite_never` | `invite_sent` |
| Jurnal | `DRY_RUN` + `facebook_landing` | `SENT` |

Poți trimite în continuare calupuri de email către prospecti importați, chiar dacă au completat mai întâi formularul Facebook fără să termine contul.

**Excepție corectă:** dacă prospectul **a terminat** crearea contului, Add USER nu mai trimite (are deja cont).

## Text scurt pentru postare Facebook (exemplu)

> Vrei să listezi animale sau să te înscrii ca partener EU-Adopt?  
> Completează formularul scurt: **https://eu-adopt.ro/inscriere/**  
> Participarea în etapa de pre-lansare este gratuită. După datele de contact vei completa formularul de cont și verificarea prin SMS și email.

## Staff

- Lead-urile noi sau actualizate apar în **Add USER** cu notă `Sursă: formular /inscriere/ (Facebook)`.
- Trimiterile reale rămân din panoul Add USER (val, plafon zilnic, cooldown după SMTP).
