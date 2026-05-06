"""Tests sur la gestion des affaires (slugify, listing, init demo)."""

from i2ao.affaires import _slugify, lister_affaires, initialiser_demo_si_absente


def test_slugify_basique():
    assert _slugify("OPH des Vallées de l'Isère") == "oph-des-vallees-de-l-isere"
    assert _slugify("Commune de Saint-Marcellin") == "commune-de-saint-marcellin"


def test_slugify_caracteres_speciaux():
    assert _slugify("Réfèction & ÇOIN du château") == "refection-coin-du-chateau"


def test_slugify_chaine_vide():
    assert _slugify("!!!") == "ao"
    assert _slugify("") == "ao"


def test_slugify_minuscule():
    assert _slugify("ABC") == "abc"


def test_initialiser_demo_creee_les_affaires():
    """Après init, les 2 affaires de démo doivent exister."""
    initialiser_demo_si_absente()
    affaires = lister_affaires()
    slugs = {a.slug for a in affaires}
    # Au moins une des deux démos doit être présente
    demos_attendues = {"demo-oph-vallees-isere", "demo-confortement-saint-marcellin"}
    assert demos_attendues & slugs, "Aucune affaire de démo créée"
