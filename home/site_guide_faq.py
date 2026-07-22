"""
FAQ Ghid EU-Adopt — doar funcționalitate site (fără medical / intern).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SiteGuideFaqEntry:
    id: str
    title: str
    keywords: tuple[str, ...]
    answer: str


SITE_GUIDE_QUICK_CHIP_IDS: tuple[str, ...] = (
    "cont_cum",
    "pt_unde",
    "adopt_cum",
    "ilove_ce",
    "mypet_ce",
    "mesaje_unde",
)


REFUSE_MEDICAL = (
    "Mulțumim — e o întrebare importantă pentru binele animalului.\n\n"
    "Ghidul EU-Adopt te ajută doar cu **navigarea pe site** (cont, animale, mesaje, favorite). "
    "Nu putem oferi sfaturi medicale sau de sănătate aici.\n\n"
    "**Ce poți face acum:** pe fișa animalului, folosește mesajele către adăpost sau asociație.\n\n"
    "**Pe viitor:** lucrăm la o zonă în care medici și veterinari parteneri vor putea răspunde "
    "voluntar la întrebări generale. Când va fi disponibilă, o vei vedea anunțată pe site.\n\n"
    "Pentru urgențe, contactează un cabinet veterinar."
)

REFUSE_OUT_OF_SCOPE = (
    "Pot explica doar **cum funcționează site-ul EU-Adopt** — cont, Prietenul tău, I Love, MyPet, mesaje.\n\n"
    "Pentru o întrebare medicală, legală sau despre un animal anume, folosește **mesajele de pe fișă** "
    "sau pagina **Contact**."
)

REFUSE_NO_MATCH = (
    "Nu am găsit un răspuns pregătit exact pentru formularea asta.\n\n"
    "Pentru animale (câini, pisici, **hamster**, iepuri etc.): meniu **Prietenul tău** → tab **Altele** → **Filtre**.\n"
    "Reformulează întrebarea sau scrie-ne pe **Contact**."
)


# Context pentru Gemini (și referință FAQ) — doar UI public, fără detalii tehnice.
SITE_GUIDE_KNOWLEDGE = """
MENIU PRINCIPAL (navbar):
- Acasă, Prietenul tău, Servicii, Transport, Shop, MyPet (după rol), I Love, Termeni, Contact, Intră / cont.
- Icon plic = mesaje (inbox unificat la Cont → Mesaje).
- Contor ❤️ = câte animale ai la I Love; 🛒 = coș (oferte/produse adăugate din site).
- Avatar + nume = Cont (profil, editare, deconectare).

ACASĂ (/):
- Pagină principală: promovări, acces rapid. Lista completă animale = Prietenul tău.

PRIETENUL TĂU (/pets/):
- Grila P2: carduri animal; scroll încarcă loturi (ex. 24).
- Butoane mobil: Găsește-mi perechea | Filtre | Ajută un Suflet (după layout).
- Găsește-mi perechea: alegi trăsături/comportament → site propune potriviri în grilă.
- Filtre P4 (desktop) sau panou Filtre (mobil): Județ, Talie, Vârstă, Sex; taburi specie Toate/Câini/Pisici/Altele.
- Resetează filtre. Mobil: Filtre rămân deschise la selecție; închizi cu ↑ sau după OK (după versiune).
- Card: inimioară (I Love), click pe imagine/card → fișă.

FIȘĂ ANIMAL (/caini/<slug>/, /pisici/<slug>/, /altele/<slug>/ sau /pets/<id>/):
- Poze (galerie, mărire pe mobil/desktop), descriere, date, stare adopție.
- Cerere adopție (PF autentificat). Mesaje conform regulilor de pe fișă.
- Inimioară, eventual link transport din adopție.

ADOPȚIE:
- PF: cerere pe fișă → MyPet mesaje la adăpost → Accept/Respinge → mesaje după accept → Finalizează adopție.

I LOVE (/i-love/): favorite salvate. Coș I Love (/i-love/cos/ sau similar): oferte/produse adăugate la coș din Servicii/Shop.

MYPET (/mypet/): adăpost/ONG — animale, mesaje, cereri, publicare.

SERVICII (/servicii/): Județ, Oraș/Loc, Resetează; Câini/Pisici/Altele; taburi Veterinare/Magazine/Saloane; card → detaliu; coș pe ofertă unde există.

SHOP (/shop/): produse, taburi; subpagini magazin foto / comenzi personalizate când sunt în meniu.

TRANSPORT (/transport/): formular cerere; T1/T2/T3 pe pagină; legătură din adopție dacă apare.

CONT (/cont/): profil, Editează, Mesaje, puncte de lucru (colaborator), ștergere cont.
Înregistrare: Intră → Creează cont → PF / ONG / Colaborator → SMS → email activare.

CONTACT (/contact/): formular echipă EU-Adopt (nu înlocuiește mesajele pe fișă animal).

ADĂPOSTURI: pagini publice adăpost (ex. /adaposturi/<slug>/) cu animalele adăpostului.

Nu da sfaturi medicale, nutriție sau legale. Răspunde doar despre navigare și funcții site.
"""


SITE_GUIDE_FAQ: tuple[SiteGuideFaqEntry, ...] = (
    SiteGuideFaqEntry(
        id="cont_cum",
        title="Cum îmi fac cont?",
        keywords=(
            "cont", "inregistr", "înregistr", "creez", "fac cont", "signup", "cont nou",
        ),
        answer=(
            "Apasă **Intră / Fă cont** din meniu → **Creează cont** → alegi tipul:\n"
            "• **Persoană fizică** — pentru adopții și favorite\n"
            "• **Adăpost / ONG / Firmă** — pentru publicare animale\n"
            "• **Colaborator** — cabinet, magazin, servicii, transport\n\n"
            "Completezi formularul, confirmi telefonul (SMS), apoi activezi contul din linkul primit pe **email**."
        ),
    ),
    SiteGuideFaqEntry(
        id="cont_tipuri",
        title="Ce tipuri de cont există?",
        keywords=("tip cont", "tipuri", "pf", "ong", "colaborator", "persoana fizica", "adăpost"),
        answer=(
            "**Persoană fizică** — poți salva animale la I Love, trimite cereri de adopție și mesaje (după accept).\n"
            "**Adăpost / ONG / Firmă** — publici și gestionezi animale în MyPet.\n"
            "**Colaborator** — partener (cabinet, magazin, servicii, transport) cu profil dedicat."
        ),
    ),
    SiteGuideFaqEntry(
        id="cont_activare",
        title="Cum activez contul după înregistrare?",
        keywords=("activ", "email", "link", "verific", "confirm", "sms"),
        answer=(
            "După formular: **verificare SMS** (cod primit pe telefon), apoi **verificare email** "
            "(link de activare). Deschide linkul din email — contul devine activ și te poți autentifica.\n\n"
            "Dacă linkul a expirat, pe ecranul „Verifică email” poți cere **retrimitere** (cu limite de siguranță)."
        ),
    ),
    SiteGuideFaqEntry(
        id="login_cum",
        title="Cum mă autentific?",
        keywords=("login", "intru", "autentif", "parola", "parolă", "email"),
        answer=(
            "Meniu → **Intră** (sau **Intră / Fă cont**). Introdu **email sau nume utilizator** și **parola**.\n\n"
            "Ai uitat parola? Folosește **Ți-ai uitat parola** de pe pagina de login."
        ),
    ),
    SiteGuideFaqEntry(
        id="pt_specie_altele",
        title="Cum găsesc hamster / iepuri / alte specii?",
        keywords=(
            "hamster", "hamsteri", "iepure", "iepuri", "porcusor", "porcușor", "guineea", "cobai",
            "chinchilla", "papagal", "broasca", "broască", "testoasa", "țestoasă", "altele", "alta specie",
            "alte animale", "specie mica", "specie mică", "rozatoare", "rozătoare",
        ),
        answer=(
            "Pentru **hamster**, iepuri și alte specii (nu câini/pisici):\n\n"
            "1. Din meniu deschide **Prietenul tău** (/pets/).\n"
            "2. Apasă tabul **Altele** (lângă Câini / Pisici) — lista arată doar animale din categoria Altele.\n"
            "3. Opțional: **Filtre** (mobil) sau panoul **P4** (desktop) — **Județ**, **Vârstă**, **Sex**, apoi **OK** sau aplică.\n"
            "4. Derulează grila **P2**; click pe card → **fișa** animalului.\n\n"
            "Dacă nu apare niciun rezultat, înseamnă că momentan nu avem anunț public pentru acea specie — revino mai târziu sau folosește **Contact**."
        ),
    ),
    SiteGuideFaqEntry(
        id="pt_unde",
        title="Unde găsesc animalele?",
        keywords=("animale", "caini", "câini", "pisici", "unde", "gasesc", "găsesc", "prietenul", "pt", "lista"),
        answer=(
            "Din meniu apasă **Prietenul tău** — vei vedea grila cu animale disponibile.\n"
            "Apasă pe un card pentru **fișa** animalului (poze, detalii, mesaje)."
        ),
    ),
    SiteGuideFaqEntry(
        id="pt_cautare",
        title="Cum caut / filtrez animale?",
        keywords=(
            "caut", "filtru", "filtre", "filtr", "judet", "județ", "talie", "marime", "mărime",
            "varsta", "vârstă", "sex", "mascul", "femela", "specie", "caini", "câini", "pisici",
            "reseteaza", "resetează", "pereche", "search", "prietenul",
        ),
        answer=(
            "Pe **Prietenul tău** (/pets/):\n\n"
            "1. Deschide **Filtre** (mobil) sau folosește panoul de filtre din **P4** (desktop).\n"
            "2. Alege **specia**: Toate, Câini, Pisici sau Altele (taburile de sus).\n"
            "3. Setează din dropdown-uri:\n"
            "   • **Județ** — un județ din România sau „Toate”\n"
            "   • **Talie** — Mică, Medie, Mare\n"
            "   • **Vârstă** — de la „<1 an” până la „10+ ani”\n"
            "   • **Sex** — Mascul sau Femelă\n"
            "4. Pe mobil apasă **OK**; pe desktop lista se actualizează la submit.\n"
            "5. **Resetează filtre** șterge toate selecțiile.\n\n"
            "Lista **P2** se derulează; la coborâre se încarcă automat mai multe carduri (câte 24)."
        ),
    ),
    SiteGuideFaqEntry(
        id="adopt_cum",
        title="Cum adopt un animal?",
        keywords=("adopt", "adopție", "adoptie", "cerere", "vreau"),
        answer=(
            "Ai nevoie de cont **persoană fizică**.\n\n"
            "1. Deschide **fișa** animalului (Prietenul tău → click pe card).\n"
            "2. Trimite **cererea de adopție** (buton dedicat pe fișă).\n"
            "3. Proprietarul/adăpostul vede cererea în **MyPet → Mesaje** și o poate accepta sau respinge.\n"
            "4. După **accept**, poți comunica prin mesaje pe fișă.\n"
            "5. Proprietarul marchează **adopția finalizată** când procesul s-a încheiat."
        ),
    ),
    SiteGuideFaqEntry(
        id="adopt_contact",
        title="Când văd datele de contact?",
        keywords=("contact", "telefon", "date", "accept", "confiden"),
        answer=(
            "Datele tale de contact nu sunt trimise proprietarului **înainte** de accept.\n"
            "După ce acceptă cererea în MyPet, fluxul de mesaje / email vă pune în legătură conform regulilor site-ului."
        ),
    ),
    SiteGuideFaqEntry(
        id="adopt_stare",
        title="Ce înseamnă starea de pe fișă?",
        keywords=("stare", "adoptat", "disponibil", "in curs", "în curs", "status"),
        answer=(
            "Pe fișă vezi dacă animalul e **disponibil**, are **adopție în curs** sau e deja **adoptat**.\n"
            "Dacă e adoptat, nu mai poți trimite o cerere nouă pentru acel anunț."
        ),
    ),
    SiteGuideFaqEntry(
        id="ilove_ce",
        title="Ce este I Love?",
        keywords=("i love", "ilove", "inima", "inimioara", "inimioară", "favorite", "salvez"),
        answer=(
            "**I Love** este lista ta de animale favorite.\n"
            "Apasă **inimioara** pe un card (Prietenul tău) sau pe fișă — trebuie să fii autentificat.\n"
            "Vezi lista din meniu → **I Love**."
        ),
    ),
    SiteGuideFaqEntry(
        id="mypet_ce",
        title="Ce este MyPet?",
        keywords=("mypet", "my pet", "panou", "gestion", "anunt", "anunț"),
        answer=(
            "**MyPet** este zona ta de lucru dacă ești adăpost, ONG sau ai permisiuni de publicare.\n"
            "Aici vezi animalele tale, **mesajele**, cererile de adopție și acțiunile (accept, respinge, finalizează)."
        ),
    ),
    SiteGuideFaqEntry(
        id="mesaje_unde",
        title="Unde văd mesajele?",
        keywords=("mesaj", "mesaje", "inbox", "plic", "convers"),
        answer=(
            "Iconița de **mesaje** din navbar (plic) duce la inbox-ul unificat.\n"
            "Pe fișa unui animal poți trimite mesaje **după acceptarea** cererii de adopție (sau conform regulilor afișate pe fișă).\n"
            "Proprietarii gestionează cererile din **MyPet**."
        ),
    ),
    SiteGuideFaqEntry(
        id="servicii_ce",
        title="Ce este pagina Servicii?",
        keywords=(
            "servicii", "cabinet", "veterinar", "grooming", "salon", "magazin partener",
            "filtru servicii", "judet servicii", "oras servicii",
        ),
        answer=(
            "**Servicii** (/servicii/) — director parteneri EU-Adopt.\n\n"
            "**Filtre (zona S2):**\n"
            "• **Județ** — tastezi sau alegi din listă\n"
            "• **Oraș/Loc** — localitatea\n"
            "• **Resetează** — șterge filtrele geografice\n\n"
            "**Specie (S2.1):** butoane **CÂINI**, **PISICI**, **ALTELE** — restrâng ofertele afișate.\n\n"
            "**Categorii (taburi):**\n"
            "• **Veterinare** — cabinete\n"
            "• **Magazine** — pet shop-uri partenere\n"
            "• **Saloane** — grooming\n\n"
            "Apasă pe un **card** pentru detaliile ofertei / partenerului."
        ),
    ),
    SiteGuideFaqEntry(
        id="shop_ce",
        title="Ce este Shop?",
        keywords=("shop", "magazin", "cumpar", "cumpăr", "produs"),
        answer=(
            "**Shop** este magazinul site-ului — produse și secțiuni dedicate (ex. magazin foto, comenzi personalizate), "
            "după ce sunt active în meniu."
        ),
    ),
    SiteGuideFaqEntry(
        id="transport_ce",
        title="Ce este Transport?",
        keywords=(
            "transport", "curier", "deplasare", "masina", "masină", "formular transport",
            "adoptie transport", "adopție transport", "from_adoption",
        ),
        answer=(
            "**Transport** (/transport/) — cereri de transport pentru animale prin platformă.\n\n"
            "1. Mergi la **Transport** din meniu (sau link din fluxul de **adopție**, dacă apare pe fișă).\n"
            "2. Completezi **formularul**: loc plecare, destinație, date relevante, detalii despre animal/călătorie.\n"
            "3. Trimiți cererea; transportatorii parteneri pot prelua din panoul lor (după regulile active).\n\n"
            "Nu înlocuiește decizia adăpostului — e un canal de cerere organizată pe site."
        ),
    ),
    SiteGuideFaqEntry(
        id="home_ce",
        title="Ce găsesc pe Acasă?",
        keywords=("home", "acasă", "acasa", "prima pagina", "prima pagină"),
        answer=(
            "**Acasă** este pagina principală: animale promovate, acces rapid la secțiuni și informații despre platformă.\n"
            "Pentru lista completă de animale, folosește **Prietenul tău**."
        ),
    ),
    SiteGuideFaqEntry(
        id="cont_edit",
        title="Cum îmi modific datele din cont?",
        keywords=("editez", "modific", "schimb", "profil", "contul meu", "telefon nou"),
        answer=(
            "Autentifică-te → **Cont** (sau linkul tău de profil) → **Editează**.\n"
            "Dacă schimbi **telefonul**, vei confirma prin SMS; dacă schimbi **emailul**, prin link de confirmare."
        ),
    ),
    SiteGuideFaqEntry(
        id="contact_unde",
        title="Cum contactez echipa EU-Adopt?",
        keywords=("contact", "suport", "help", "ajutor", "problema", "problemă", "eroare"),
        answer=(
            "Pagina **Contact** din meniu — formular pentru întrebări tehnice sau despre platformă.\n"
            "Pentru un **animal anume**, folosește mesajele de pe fișa lui."
        ),
    ),
    SiteGuideFaqEntry(
        id="pt_match",
        title="Ce face „Găsește-mi perechea”?",
        keywords=(
            "pereche", "potrivire", "match", "gaseste-mi", "găsește-mi", "compatibil",
            "caracter", "comportament", "traits", "trăsături",
        ),
        answer=(
            "Pe **Prietenul tău**, butonul **Găsește-mi perechea** deschide un ghid scurt:\n\n"
            "1. Alegi trăsături / preferințe (comportament, stil de viață — opțiunile din modal).\n"
            "2. Confirmi — site-ul filtrează sau evidențiază animale **potrivite** în grila P2.\n"
            "3. Poți combina cu **Filtre** (județ, talie, vârstă, specie Câini/Pisici/Altele).\n"
            "4. Click pe un card → **fișă** → cerere adopție dacă e disponibil.\n\n"
            "Nu garantează adopția; te ajută să găsești mai repede animale aliniate preferințelor tale."
        ),
    ),
    SiteGuideFaqEntry(
        id="fisa_animal",
        title="Ce pot face pe fișa unui animal?",
        keywords=(
            "fisa", "fișă", "pagina animal", "poze", "galerie", "detalii", "slug",
            "caini", "pisici", "altele", "fullscreen", "imagine",
        ),
        answer=(
            "Pe **fișa** animalului (din Prietenul tău → click card):\n\n"
            "• Vezi **poze** (galerie; pe mobil poți mări/pinch-zoom unde e activ).\n"
            "• Citești descrierea, vârstă, locație, **starea** adopției.\n"
            "• **Inimioară** → salvezi la **I Love** (cont autentificat).\n"
            "• **Cerere adopție** — dacă ești PF și animalul e disponibil.\n"
            "• **Mesaje** — după regulile afișate (uneori după accept cerere).\n"
            "• Link **Transport** — dacă apare în fluxul de adopție.\n\n"
            "URL-uri tip: /caini/…, /pisici/…, /altele/… (specie + nume slug)."
        ),
    ),
    SiteGuideFaqEntry(
        id="ilove_cos",
        title="I Love și coșul din navbar",
        keywords=("cos", "coș", "cos cumparaturi", "checkout", "oferta cos", "site cart", "i love cos"),
        answer=(
            "**I Love** (meniu sau ❤️ în navbar): animale favorite — apeși inimioara pe card/fișă.\n\n"
            "**Coș** (🛒 în navbar): oferte sau produse adăugate din **Servicii** / **Shop** (buton coș pe card unde există).\n"
            "Deschizi coșul din navbar → verifici lista → finalizezi conform pașilor afișați (checkout).\n\n"
            "Contorul de lângă iconițe arată câte elemente ai salvate."
        ),
    ),
    SiteGuideFaqEntry(
        id="navbar_ce",
        title="Ce înseamnă iconițele din navbar?",
        keywords=("navbar", "meniu", "plic", "mesaje navbar", "avatar", "contor", "hamburger"),
        answer=(
            "• **Hamburger** (mobil): deschide meniul cu toate paginile.\n"
            "• **Plic**: mesaje — duce la inbox (Cont → Mesaje).\n"
            "• **❤️ + număr**: câte animale la **I Love**.\n"
            "• **🛒 + număr**: câte articole în **coș**.\n"
            "• **Avatar / nume**: **Cont** — profil, editare, deconectare.\n"
            "• **Intră**: login sau înregistrare dacă nu ești autentificat."
        ),
    ),
    SiteGuideFaqEntry(
        id="adapost_cautare",
        title="Cum găsesc un adăpost sau ONG?",
        keywords=(
            "gasesc adapost",
            "găsesc adăpost",
            "caut adapost",
            "caut adăpost",
            "gasesc ong",
            "găsesc ong",
            "lista adaposturi",
            "lista adăposturi",
            "adaposturi",
            "asociatii",
            "asociații",
            "unde e adapostul",
            "unde e adăpostul",
        ),
        answer=(
            "Deschide **/adaposturi/** — directorul cu **adăposturi și ONG-uri** de pe EU-Adopt.\n\n"
            "• Filtrează după **județ** din meniul de sus.\n"
            "• Apasă pe **caseta** organizației → pagina ei cu animalele din MyPet.\n"
            "• Dacă știi numele (ex. Nicol), derulează lista sau filtrează județul și caută caseta.\n\n"
            "Animalele din toată țara: **Prietenul tău** + filtre (nu e același lucru cu lista de adăposturi)."
        ),
    ),
    SiteGuideFaqEntry(
        id="adapost_pagina",
        title="Pagina unui adăpost",
        keywords=(
            "pagina adapost",
            "pagina adăpost",
            "pagina adăpostului",
            "animalele adapostului",
            "lista caini adapost",
            "shelter page",
        ),
        answer=(
            "Fiecare adăpost din **/adaposturi/** are pagină publică (ex. **/adaposturi/nume-adapost/**):\n"
            "• Prezentare, logo, contact, animalele lui în grilă.\n"
            "• Click pe animal → aceeași **fișă** ca din Prietenul tău.\n"
            "• Pentru toate animalele din țară, folosește **Prietenul tău** + filtre."
        ),
    ),
    SiteGuideFaqEntry(
        id="inscriere_scurt",
        title="Link scurt de înscriere (Facebook etc.)",
        keywords=("inscriere", "facebook", "fb", "invitatie", "invitație", "prefill"),
        answer=(
            "Pagina **/inscriere/** — formular scurt care te duce apoi la înregistrarea completă "
            "(ONG / colaborator / PF) cu date **precompletate** unde e cazul.\n"
            "Util pentru linkuri din social media către EU-Adopt."
        ),
    ),
    SiteGuideFaqEntry(
        id="termeni_unde",
        title="Unde sunt termenii și GDPR?",
        keywords=("termeni", "gdpr", "confiden", "cookie", "legal"),
        answer=(
            "Link **Termeni și condiții** în meniu, plus politici de confidențialitate și cookie-uri "
            "(accesibile din footer/meniu, după cum sunt afișate pe site)."
        ),
    ),
)
