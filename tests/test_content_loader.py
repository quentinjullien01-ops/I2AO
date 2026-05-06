"""Tests sur le chargement de la bibliothèque MT et du catalogue DPGF."""

from i2ao.content_loader import load_dpgf_catalog, load_mt_library, load_repair_profile


def test_mt_library_charge_tous_les_paragraphes():
    paragraphes = load_mt_library()
    assert len(paragraphes) >= 10, "Au moins 10 paragraphes attendus dans la bibliothèque MT"
    ids = {p.id for p in paragraphes}
    # Vérifier la présence de paragraphes critiques
    attendus = {
        "mt-01-presentation-candidat",
        "mt-02-comprehension-contexte",
        "mt-03-methodologie-diagnostic",
        "mt-04-methodologie-moe-confortement",
        "mt-05-approche-rga",
        "mt-06-site-occupe",
        "mt-07-moyens-humains",
    }
    manquants = attendus - ids
    assert not manquants, f"Paragraphes manquants : {manquants}"


def test_mt_library_paragraphes_ont_du_contenu():
    paragraphes = load_mt_library()
    for p in paragraphes:
        assert p.section, f"section vide pour {p.id}"
        assert len(p.contenu) > 200, f"contenu trop court pour {p.id}"
        assert p.ordre > 0


def test_mt_library_paragraphes_ordonnes():
    paragraphes = load_mt_library()
    ordres = [p.ordre for p in paragraphes]
    assert ordres == sorted(ordres), "Paragraphes pas triés par ordre"


def test_dpgf_catalog_charge_les_prestations():
    catalog = load_dpgf_catalog()
    assert len(catalog) >= 30, "Catalogue DPGF doit contenir au moins 30 prestations"
    codes = {p.code for p in catalog}
    assert len(codes) == len(catalog), "Codes prestation non uniques"


def test_dpgf_catalog_categories_presentes():
    catalog = load_dpgf_catalog()
    categories = {p.categorie for p in catalog}
    attendues = {
        "Diagnostic structurel",
        "Investigations non destructives",
        "Investigations destructives",
        "Maîtrise d'œuvre confortement",
        "Expertise",
    }
    manquantes = attendues - categories
    assert not manquantes, f"Catégories manquantes : {manquantes}"


def test_dpgf_catalog_prix_positifs():
    catalog = load_dpgf_catalog()
    for p in catalog:
        assert p.prix_unitaire > 0, f"Prix invalide pour {p.code}"


def test_repair_profile_charge():
    profile = load_repair_profile()
    assert profile, "Profil Repair vide"
    assert "Repair" in profile or "repair" in profile.lower()
