"""Tests sur le parser PDF et la détection de type de pièce."""

from pathlib import Path

import pytest

from i2ao.pdf_parser import detect_type_piece, parse_pdf

DEMO_DCE_DIR = Path(__file__).resolve().parents[1] / "data" / "samples" / "dce-oph-isere"


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("RC_consultation.pdf", "RC"),
        ("Reglement_consultation.pdf", "RC"),
        ("Reglement de consultation.pdf", "RC"),
        ("CCTP_lot1.pdf", "CCTP"),
        ("CCTP-lot-structure.pdf", "CCTP"),
        ("CCAP.pdf", "CCAP"),
        ("AE.pdf", "AE"),
        ("Acte_engagement.pdf", "AE"),
        ("BPU_lot_structure.pdf", "BPU"),
        ("DPGF.pdf", "DPGF"),
        ("DQE.pdf", "DQE"),
        ("plan_RDC.pdf", "autre"),
        ("rapport_diagnostic.pdf", "autre"),
        ("annexe1.pdf", "autre"),
    ],
)
def test_detect_type_piece_par_nom_fichier(filename, expected):
    assert detect_type_piece(filename) == expected


def test_detect_type_piece_filename_prevaut_sur_contenu():
    """BPU.pdf qui cite le CCAP en référence croisée doit rester BPU."""
    contenu = "Le candidat se reportera au CCAP article 5 pour les modalités de paiement."
    assert detect_type_piece("BPU.pdf", contenu) == "BPU"


def test_detect_type_piece_fallback_sur_contenu():
    """Filename générique mais contenu RC explicite."""
    contenu = "Règlement de consultation\n\nArticle 1 — Identification du pouvoir adjudicateur"
    assert detect_type_piece("doc_acheteur.pdf", contenu) == "RC"


@pytest.mark.skipif(
    not (DEMO_DCE_DIR / "RC.pdf").exists(),
    reason="DCE de démo non généré (lancer scripts/generate_demo_dce.py)",
)
def test_parse_pdf_demo_rc():
    """Vérifie l'extraction du RC du DCE de démo."""
    result = parse_pdf(DEMO_DCE_DIR / "RC.pdf")
    assert result.nb_pages > 3
    assert len(result.texte_normalise) > 5000
    assert result.methode == "pdfplumber"
    assert result.est_probablement_scanne is False
    # Mots-clés métier qu'on s'attend à trouver
    assert "Règlement" in result.texte or "Reglement" in result.texte or "règlement" in result.texte
    assert "consultation" in result.texte.lower()


@pytest.mark.skipif(
    not (DEMO_DCE_DIR / "CCTP.pdf").exists(),
    reason="DCE de démo non généré",
)
def test_parse_pdf_demo_cctp_contient_termes_metier():
    """Vérifie que le CCTP contient bien les termes métier pathologie."""
    result = parse_pdf(DEMO_DCE_DIR / "CCTP.pdf")
    contenu = result.texte_normalise.lower()
    assert "rga" in contenu or "retrait" in contenu
    assert "confortement" in contenu or "consolidation" in contenu
    assert "diagnostic" in contenu


def test_parse_pdf_bytes():
    """Le parser fonctionne avec des bytes en entrée."""
    pdf_path = DEMO_DCE_DIR / "RC.pdf"
    if not pdf_path.exists():
        pytest.skip("DCE de démo non généré")
    data = pdf_path.read_bytes()
    result = parse_pdf(data, nom_fichier="custom.pdf")
    assert result.nom_fichier == "custom.pdf"
    assert result.nb_pages > 3


def test_parse_pdf_scanne_detecte():
    """Un PDF vide (image scannée simulée) est correctement marqué comme scanné."""
    import fitz

    doc = fitz.open()
    doc.new_page(width=595, height=842)
    data = doc.tobytes()
    doc.close()

    result = parse_pdf(data, nom_fichier="scanne.pdf", autoriser_ocr=False)
    assert result.est_probablement_scanne is True
    assert result.methode == "vide-probable-scanne"
    assert len(result.avertissements) == 1
    # L'avertissement mentionne soit l'installation de Tesseract, soit l'échec OCR.
    avert = result.avertissements[0].lower()
    assert "tesseract" in avert or "scanné" in avert or "scanne" in avert


def test_is_ocr_available_renvoie_bool():
    """La fonction de détection ne lève jamais d'exception."""
    from i2ao.pdf_parser import is_ocr_available

    result = is_ocr_available()
    assert isinstance(result, bool)
