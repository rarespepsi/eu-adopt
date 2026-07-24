"""Campanii.ro — sterilizări / info pe județe (stub + date județe)."""

from __future__ import annotations

from dataclasses import dataclass

from home.ro_location import all_counties, fold_key


# Cod auto (AB, CJ, …) — aliniat cu id-urile SVG `ro-ab`, `ro-cj`, …
_COUNTY_CODES: dict[str, str] = {
    "Alba": "AB",
    "Arad": "AR",
    "Argeș": "AG",
    "Bacău": "BC",
    "Bihor": "BH",
    "Bistrița-Năsăud": "BN",
    "Botoșani": "BT",
    "Brăila": "BR",
    "Brașov": "BV",
    "București": "B",
    "Buzău": "BZ",
    "Călărași": "CL",
    "Caraș-Severin": "CS",
    "Cluj": "CJ",
    "Constanța": "CT",
    "Covasna": "CV",
    "Dâmbovița": "DB",
    "Dolj": "DJ",
    "Galați": "GL",
    "Giurgiu": "GR",
    "Gorj": "GJ",
    "Harghita": "HR",
    "Hunedoara": "HD",
    "Ialomița": "IL",
    "Iași": "IS",
    "Ilfov": "IF",
    "Maramureș": "MM",
    "Mehedinți": "MH",
    "Mureș": "MS",
    "Neamț": "NT",
    "Olt": "OT",
    "Prahova": "PH",
    "Sălaj": "SJ",
    "Satu Mare": "SM",
    "Sibiu": "SB",
    "Suceava": "SV",
    "Teleorman": "TR",
    "Timiș": "TM",
    "Tulcea": "TL",
    "Vâlcea": "VL",
    "Vaslui": "VS",
    "Vrancea": "VN",
}

# Reședințe / localități principale (afișare pe hartă + pe pagina județului)
_COUNTY_MAIN_CITIES: dict[str, tuple[str, ...]] = {
    "Alba": ("Alba Iulia", "Sebeș", "Aiud"),
    "Arad": ("Arad", "Ineu", "Lipova"),
    "Argeș": ("Pitești", "Câmpulung", "Curtea de Argeș"),
    "Bacău": ("Bacău", "Onești", "Moinești"),
    "Bihor": ("Oradea", "Salonta", "Beiuș"),
    "Bistrița-Năsăud": ("Bistrița", "Năsăud", "Beclean"),
    "Botoșani": ("Botoșani", "Dorohoi", "Săveni"),
    "Brăila": ("Brăila", "Ianca", "Însurăței"),
    "Brașov": ("Brașov", "Făgăraș", "Săcele"),
    "București": ("București",),
    "Buzău": ("Buzău", "Râmnicu Sărat", "Nehoiu"),
    "Călărași": ("Călărași", "Oltenița", "Budești"),
    "Caraș-Severin": ("Reșița", "Caransebeș", "Oravița"),
    "Cluj": ("Cluj-Napoca", "Turda", "Dej"),
    "Constanța": ("Constanța", "Mangalia", "Medgidia"),
    "Covasna": ("Sfântu Gheorghe", "Târgu Secuiesc", "Covasna"),
    "Dâmbovița": ("Târgoviște", "Moreni", "Pucioasa"),
    "Dolj": ("Craiova", "Băilești", "Calafat"),
    "Galați": ("Galați", "Tecuci", "Târgu Bujor"),
    "Giurgiu": ("Giurgiu", "Bolintin-Vale", "Mihăilești"),
    "Gorj": ("Târgu Jiu", "Motru", "Rovinari"),
    "Harghita": ("Miercurea Ciuc", "Odorheiu Secuiesc", "Gheorgheni"),
    "Hunedoara": ("Deva", "Hunedoara", "Petroșani"),
    "Ialomița": ("Slobozia", "Fetești", "Urziceni"),
    "Iași": ("Iași", "Pașcani", "Hârlău"),
    "Ilfov": ("Buftea", "Voluntari", "Otopeni"),
    "Maramureș": ("Baia Mare", "Sighetu Marmației", "Borșa"),
    "Mehedinți": ("Drobeta-Turnu Severin", "Orșova", "Strehaia"),
    "Mureș": ("Târgu Mureș", "Reghin", "Sighișoara"),
    "Neamț": ("Piatra Neamț", "Roman", "Târgu Neamț"),
    "Olt": ("Slatina", "Caracal", "Balș"),
    "Prahova": ("Ploiești", "Câmpina", "Sinaia"),
    "Sălaj": ("Zalău", "Șimleu Silvaniei", "Jibou"),
    "Satu Mare": ("Satu Mare", "Carei", "Negrești-Oaș"),
    "Sibiu": ("Sibiu", "Mediaș", "Cisnădie"),
    "Suceava": ("Suceava", "Fălticeni", "Rădăuți"),
    "Teleorman": ("Alexandria", "Roșiorii de Vede", "Turnu Măgurele"),
    "Timiș": ("Timișoara", "Lugoj", "Sânnicolau Mare"),
    "Tulcea": ("Tulcea", "Măcin", "Babadag"),
    "Vâlcea": ("Râmnicu Vâlcea", "Drăgășani", "Băile Olănești"),
    "Vaslui": ("Vaslui", "Bârlad", "Huși"),
    "Vrancea": ("Focșani", "Adjud", "Mărășești"),
}


@dataclass(frozen=True)
class CampaniiJudet:
    name: str
    slug: str
    code: str
    main_cities: tuple[str, ...]


def county_slug(name: str) -> str:
    return fold_key(name).replace(" ", "-")


def campanii_judete() -> list[CampaniiJudet]:
    out: list[CampaniiJudet] = []
    for name in all_counties():
        cities = _COUNTY_MAIN_CITIES.get(name) or (name,)
        code = _COUNTY_CODES.get(name) or ""
        out.append(
            CampaniiJudet(name=name, slug=county_slug(name), code=code, main_cities=cities)
        )
    return out


def campanii_judet_by_slug(slug: str) -> CampaniiJudet | None:
    key = fold_key((slug or "").replace("-", " "))
    for j in campanii_judete():
        if fold_key(j.slug.replace("-", " ")) == key or fold_key(j.name) == key:
            return j
    return None


def campanii_url_by_code() -> dict[str, str]:
    """{ 'AB': '/publicitate/campanii/alba/', ... } — pentru click pe SVG."""
    from django.urls import reverse

    return {
        j.code: reverse("publicitate_campanii_judet", kwargs={"judet_slug": j.slug})
        for j in campanii_judete()
        if j.code
    }
