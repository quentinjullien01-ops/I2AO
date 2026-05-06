"""Tests sur le calcul de montant DPGF (gestion % travaux vs unités)."""

from i2ao.content_loader import PrestationDPGF
from i2ao.dpgf_engine import _calculer_montant


def _prest(code: str, libelle: str, unite: str, prix: float) -> PrestationDPGF:
    return PrestationDPGF(
        code=code,
        libelle=libelle,
        unite=unite,
        prix_unitaire=prix,
        categorie="Test",
        tags=[],
    )


def test_calcul_forfait():
    p = _prest("X.01", "Forfait", "forfait", 1000.0)
    assert _calculer_montant(p, 1) == 1000.0
    assert _calculer_montant(p, 3) == 3000.0


def test_calcul_jour():
    p = _prest("X.02", "Vacation jour", "jour", 1100.0)
    assert _calculer_montant(p, 5) == 5500.0


def test_calcul_pourcent_travaux():
    """% travaux : prix_unitaire est un % et quantite est le montant travaux."""
    p = _prest("7.02", "MOE base", "% travaux", 11.0)
    # 11% de 250 000 = 27 500
    assert _calculer_montant(p, 250000) == 27500.0


def test_calcul_pourcent_travaux_alternative():
    p = _prest("7.03", "MOE", "% travaux", 9.0)
    assert _calculer_montant(p, 600000) == 54000.0


def test_calcul_pourcent_variantes_unite():
    """Le détecteur d'unité doit être tolérant aux variantes."""
    for unite in ["% travaux", "%travaux", "%", " % travaux "]:
        p = _prest("X", "X", unite, 10.0)
        assert _calculer_montant(p, 100000) == 10000.0


def test_calcul_arrondi():
    p = _prest("X", "X", "forfait", 123.456)
    assert _calculer_montant(p, 1) == 123.46
