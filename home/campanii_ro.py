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


def campanii_visible_until_cutoff():
    """Vizibil până la date_end + 3 zile (inclusiv ziua a 3-a)."""
    from datetime import date, timedelta

    return date.today() - timedelta(days=3)


def campanii_visible_queryset():
    """Campanii încă afișate public (în perioada + 3 zile după expirare)."""
    from home.models import CampanieSterilizare

    return CampanieSterilizare.objects.filter(date_end__gte=campanii_visible_until_cutoff())


def campanii_for_judet_slug(judet_slug: str):
    """Listă vizibilă pe județ, alfabetic după localitate (fără nume user)."""
    from home.ro_location import fold_key

    qs = list(
        campanii_visible_queryset()
        .filter(judet_slug=judet_slug)
        .order_by("localitate", "date_start", "pk")
    )
    qs.sort(key=lambda c: (fold_key(c.localitate or ""), c.date_start or "", c.pk))
    return qs


def campanii_count_by_code() -> dict[str, int]:
    """{ 'NT': 2, ... } — contor pe județ (cod auto) pentru harta SVG."""
    from django.db.models import Count

    slug_to_code = {j.slug: j.code for j in campanii_judete() if j.code}
    out: dict[str, int] = {}
    for row in campanii_visible_queryset().values("judet_slug").annotate(n=Count("id")):
        code = slug_to_code.get(row["judet_slug"]) or ""
        if code:
            out[code] = int(row["n"] or 0)
    return out


def campanii_for_user(user):
    """Campanii vizibile ale userului (perioadă + 3 zile), cele mai noi primele."""
    if not user or not getattr(user, "is_authenticated", False):
        return []
    return list(
        campanii_visible_queryset()
        .filter(user=user)
        .order_by("-date_start", "-pk")
    )


def resolve_campanii_judet(name_or_slug: str) -> CampaniiJudet | None:
    raw = (name_or_slug or "").strip()
    if not raw:
        return None
    by_slug = campanii_judet_by_slug(raw)
    if by_slug:
        return by_slug
    key = fold_key(raw)
    for j in campanii_judete():
        if fold_key(j.name) == key:
            return j
    return None
