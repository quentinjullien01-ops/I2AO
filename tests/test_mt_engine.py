"""Tests sur le moteur MT (détection de variables non remplies)."""

from i2ao.mt_engine import (
    MemoireTechniqueGenere,
    SectionMT,
    detecter_variables_non_remplies,
)


def _mt_avec_sections(*sections: SectionMT) -> MemoireTechniqueGenere:
    return MemoireTechniqueGenere(
        titre_marche="Test",
        pouvoir_adjudicateur="Test PA",
        candidat="Test candidat",
        sections=list(sections),
    )


def test_aucune_variable_orpheline():
    mt = _mt_avec_sections(
        SectionMT(
            paragraphe_id="p1",
            titre="Section 1",
            contenu_md="Du texte sans variable, juste de la prose.",
        )
    )
    assert detecter_variables_non_remplies(mt) == {}


def test_detecte_variable_orpheline():
    mt = _mt_avec_sections(
        SectionMT(
            paragraphe_id="p1",
            titre="Section 1",
            contenu_md="Notre intervention sur {{nom_ouvrage}} se déroulera...",
        )
    )
    result = detecter_variables_non_remplies(mt)
    assert "p1" in result
    assert result["p1"] == ["{{nom_ouvrage}}"]


def test_detecte_plusieurs_variables_meme_section():
    mt = _mt_avec_sections(
        SectionMT(
            paragraphe_id="p1",
            titre="Section 1",
            contenu_md="{{a}} et {{b}} sont restées non remplies.",
        )
    )
    result = detecter_variables_non_remplies(mt)
    assert sorted(result["p1"]) == ["{{a}}", "{{b}}"]


def test_detecte_dans_plusieurs_sections():
    mt = _mt_avec_sections(
        SectionMT(paragraphe_id="p1", titre="A", contenu_md="OK propre"),
        SectionMT(paragraphe_id="p2", titre="B", contenu_md="Pas propre {{x}}"),
        SectionMT(paragraphe_id="p3", titre="C", contenu_md="Variable {{y}}"),
    )
    result = detecter_variables_non_remplies(mt)
    assert "p1" not in result
    assert result["p2"] == ["{{x}}"]
    assert result["p3"] == ["{{y}}"]
