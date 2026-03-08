# Fixed set of 12 demo dogs – same list used across Home, Prietenul tău, profiles, etc.
# Do not add more demo dogs; use this single source.
# Each dog has a unique imagine_fallback (static path) so A2 grid shows 12 different images.
# Optional: "added_at" (datetime) for A2 selection: dogs added in last 24h appear first in A2.
# "traits" = two personality traits for PT P2 card (max 2 shown).

DEMO_DOGS = [
    {"id": 1, "nume": "Charlie", "varsta": "2 ani", "descriere": "Prietenos și jucăuș, se înțelege cu copiii.", "imagine_fallback": "images/pets/charlie-400x200.jpg", "traits": ["Prietenos", "Jucăuș"]},
    {"id": 2, "nume": "Luna", "varsta": "4 ani", "descriere": "Liniștită, ideală pentru apartament.", "imagine_fallback": "images/pets/archie1-275x275.jpg", "traits": ["Liniștită", "Blândă"]},
    {"id": 3, "nume": "Max", "varsta": "3 ani", "descriere": "Energic, iubește plimbările lungi.", "imagine_fallback": "images/pets/candy1-275x275.jpeg", "traits": ["Energic", "Activist"]},
    {"id": 4, "nume": "Bella", "varsta": "5 ani", "descriere": "Dulce și devotată, adoptată din adăpost.", "imagine_fallback": "images/pets/chance1-275x275.jpg", "traits": ["Dulce", "Devotată"]},
    {"id": 5, "nume": "Rex", "varsta": "2 ani", "descriere": "Tânăr și curios, dresat la bază.", "imagine_fallback": "images/pets/chester1-275x275.jpg", "traits": ["Curios", "Dresat"]},
    {"id": 6, "nume": "Daisy", "varsta": "6 ani", "descriere": "Calmă, potrivită pentru familie.", "imagine_fallback": "images/pets/cindy1-275x275.jpg", "traits": ["Calmă", "Familie"]},
    {"id": 7, "nume": "Bruno", "varsta": "3 ani", "descriere": "Fidel și protectiv, bun paznic.", "imagine_fallback": "images/pets/grissom1-275x275.jpg", "traits": ["Fidel", "Protectiv"]},
    {"id": 8, "nume": "Mia", "varsta": "1 an", "descriere": "Pui activ, în căutare de jocuri.", "imagine_fallback": "images/pets/happy1-275x275.jpg", "traits": ["Activă", "Jucăușă"]},
    {"id": 9, "nume": "Rocky", "varsta": "4 ani", "descriere": "Rezistent, îi place natura.", "imagine_fallback": "images/pets/inga1-275x275.jpg", "traits": ["Rezistent", "Natură"]},
    {"id": 10, "nume": "Nala", "varsta": "2 ani", "descriere": "Sociabilă, se împrietenește cu alți câini.", "imagine_fallback": "images/pets/JazzyGirlAverill-1-275x275.jpg", "traits": ["Sociabilă", "Prietenoasă"]},
    {"id": 11, "nume": "Oscar", "varsta": "5 ani", "descriere": "Liniștit și afectuos, adaptat la interior.", "imagine_fallback": "images/pets/winston1-275x275.jpg", "traits": ["Liniștit", "Afectuos"]},
    {"id": 12, "nume": "Zara", "varsta": "3 ani", "descriere": "Inteligentă, răspunde bine la comenzi.", "imagine_fallback": "images/pets/shorty1-400x200.jpg", "traits": ["Inteligentă", "Ascultătoare"]},
]

# Fallback when a dog has no imagine_fallback (e.g. legacy code)
DEMO_DOG_IMAGE = "images/pets/charlie-400x200.jpg"

# Hero A1 (caseta cu sigle) – poze cu câini/animale care se rotesc în fundal.
# Dimensiuni recomandate: landscape 2:1 sau 3:1, ex. 1200×400 px sau 1600×500 px,
# min. 800×300 px. Pozele se afișează cu object-fit: cover (umplu banda, se decupează marginile).
HERO_SLIDER_IMAGES = [
    "images/pets/charlie-400x200.jpg",
    "images/pets/charlie-600x240.jpg",
    "images/pets/chester1-600x240.jpg",
    "images/pets/cindy1-600x240.jpg",
    "images/pets/shorty1-400x200.jpg",
]

# A2 homepage cover – quote pool (assign randomly to cards; rotate in JS)
A2_QUOTE_POOL = [
    "Sunt și eu un suflet.",
    "Caut o familie.",
    "Adoptă, nu cumpăra.",
    "Promit să te iubesc.",
    "Aștept o casă caldă.",
    "Vrei să fim prieteni?",
    "Un suflet te caută.",
    "Cineva te așteaptă.",
    "Împreună suntem familie.",
    "Dragostea nu se cumpără.",
    "Eu te aleg pe tine.",
    "Vrei să mă iei acasă?",
    "Sunt pregătit să iubesc.",
    "O șansă schimbă o viață.",
    "Casa ta poate fi casa mea.",
    "Un prieten adevărat.",
    "Sunt aici pentru tine.",
    "Adoptă un suflet.",
    "Nu cumpăra, adoptă.",
    "Familia începe cu iubire.",
    "Cineva te așteaptă acasă.",
    "Vreau să fiu prietenul tău.",
    "Un câine, o viață schimbată.",
    "Dragostea mea e gratuită.",
    "Am nevoie de tine.",
    "Vrei să fim echipă?",
    "Un prieten loial.",
    "Sunt gata de aventuri.",
    "Pot fi familia ta.",
    "Aștept o mângâiere.",
    "Un prieten pentru viață.",
    "Un suflet pentru un suflet.",
    "Îți pot schimba ziua.",
    "Împreună e mai bine.",
    "Te aștept.",
    "Adoptă speranță.",
]
