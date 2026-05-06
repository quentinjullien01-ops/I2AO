"""Pipeline complet sur une affaire : DCE → Analyse → MT → DPGF → Couverture → Synthèse.

Usage :
    .venv/Scripts/python.exe scripts/run_pipeline.py <slug-affaire>

Ou sans argument pour lister les affaires disponibles.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from i2ao.affaires import (  # noqa: E402
    Affaire,
    get_affaire,
    initialiser_demo_si_absente,
    lister_affaires,
)
from i2ao.coverage import evaluer_couverture  # noqa: E402
from i2ao.docx_export import exporter_mt_docx  # noqa: E402
from i2ao.dpgf_engine import generer_dpgf  # noqa: E402
from i2ao.extractor import AnalyseAO, concatener_dce, extraire_analyse_ao  # noqa: E402
from i2ao.llm import LLMClient  # noqa: E402
from i2ao.mt_engine import generer_mt  # noqa: E402
from i2ao.pdf_parser import detect_type_piece, parse_pdf  # noqa: E402
from i2ao.synthese import exporter_synthese_docx, generer_synthese  # noqa: E402
from i2ao.xlsx_export import exporter_dpgf_xlsx  # noqa: E402

# Métadonnées par affaire (référence marché, candidat) pour les exports
AFFAIRE_META = {
    "demo-oph-vallees-isere": {
        "marche_ref": "Marché 2026-MOE-STRUCT-01",
        "candidat": "Repair Ingénierie",
    },
    "demo-confortement-saint-marcellin": {
        "marche_ref": "Marché 2026-MAPA-MOE-04",
        "candidat": "Repair Ingénierie",
    },
}


def _meta_pour(slug: str) -> dict[str, str]:
    return AFFAIRE_META.get(
        slug,
        {"marche_ref": slug, "candidat": "Repair Ingénierie"},
    )


def _afficher_usage(affaires: list[Affaire]) -> None:
    print("Usage : python scripts/run_pipeline.py <slug-affaire>\n")
    if not affaires:
        print("Aucune affaire trouvée.")
        return
    print("Affaires disponibles :")
    for a in affaires:
        statut = []
        statut.append("DCE" if a.has_pieces() else "  -")
        statut.append("Ana" if a.has_analyse() else "  -")
        statut.append("MT " if a.has_mt() else "  -")
        statut.append("DPG" if a.has_dpgf() else "  -")
        statut.append("Cov" if a.has_couverture() else "  -")
        statut.append("Syn" if a.has_synthese() else "  -")
        print(f"  [{' '.join(statut)}]  {a.slug}")


def lancer_pipeline(affaire: Affaire, client: LLMClient) -> int:
    if not affaire.has_pieces():
        print(f"L'affaire '{affaire.slug}' n'a pas de pièces déposées.")
        return 1

    meta = _meta_pour(affaire.slug)
    print(f"=== Pipeline complet — {affaire.nom} ===\n")

    print("[1/6] Lecture des pieces PDF…")
    pieces = []
    for pdf in sorted(affaire.pieces_dir.glob("*.pdf")):
        r = parse_pdf(pdf)
        type_p = detect_type_piece(pdf.name, r.texte_normalise)
        pieces.append((type_p, r.texte_normalise))
        flag = "  ⚠️" if r.est_probablement_scanne else ""
        print(f"      {pdf.name:30} -> {type_p:6} pages={r.nb_pages:2} ({r.methode}){flag}")
    dce = concatener_dce(pieces)
    print(f"      DCE concatene : {len(dce):,} caracteres".replace(",", " "))

    print("\n[2/6] Extraction structuree de l'AO…")
    analyse = extraire_analyse_ao(client, dce)
    affaire.analyse_path.write_text(analyse.model_dump_json(indent=2), encoding="utf-8")
    print(f"      -> {len(analyse.exigences)} exigences extraites")

    print("\n[3/6] Generation du memoire technique…")
    mt = generer_mt(client, analyse)
    affaire.mt_json_path.write_text(mt.model_dump_json(indent=2), encoding="utf-8")
    exporter_mt_docx(mt, affaire.mt_docx_path)
    size_kb = affaire.mt_docx_path.stat().st_size / 1024
    print(f"      -> {len(mt.sections)} sections, DOCX {size_kb:.1f} KB")

    print("\n[4/6] Generation de la DPGF…")
    dpgf = generer_dpgf(client, analyse, dce)
    affaire.dpgf_json_path.write_text(dpgf.model_dump_json(indent=2), encoding="utf-8")
    exporter_dpgf_xlsx(
        dpgf,
        affaire.dpgf_xlsx_path,
        marche_ref=meta["marche_ref"],
        candidat=meta["candidat"],
    )
    size_kb = affaire.dpgf_xlsx_path.stat().st_size / 1024
    print(
        f"      -> DQE {dpgf.montant_dqe_he:,.2f} EUR HT, "
        f"{len(dpgf.dqe)} lignes, XLSX {size_kb:.1f} KB".replace(",", " ")
    )

    print("\n[5/6] Evaluation de la couverture du MT…")
    rapport = evaluer_couverture(client, analyse, mt)
    affaire.couverture_path.write_text(rapport.model_dump_json(indent=2), encoding="utf-8")
    print(
        f"      -> Score {rapport.score_pct:.0f}% "
        f"({rapport.nb_couvertes} OK / {rapport.nb_partiellement_couvertes} partielles / "
        f"{rapport.nb_non_couvertes} non / {rapport.nb_non_applicables} N/A)"
    )

    print("\n[6/6] Synthese direction Go/No-go…")
    synth = generer_synthese(client, analyse, mt, dpgf)
    affaire.synthese_json_path.write_text(synth.model_dump_json(indent=2), encoding="utf-8")
    exporter_synthese_docx(synth, affaire.synthese_docx_path, candidat=meta["candidat"])
    size_kb = affaire.synthese_docx_path.stat().st_size / 1024
    print(f"      -> {len(synth.atouts_candidat)} atouts, DOCX {size_kb:.1f} KB")

    print("\n=== Pipeline complete ===")
    print(f"Artefacts dans : {affaire.dossier.relative_to(PROJECT_ROOT)}")
    return 0


def main() -> int:
    initialiser_demo_si_absente()
    affaires = lister_affaires()

    if len(sys.argv) < 2:
        _afficher_usage(affaires)
        return 0

    slug = sys.argv[1]
    affaire = get_affaire(slug)
    if affaire is None:
        print(f"Affaire '{slug}' introuvable.\n")
        _afficher_usage(affaires)
        return 1

    client = LLMClient()
    return lancer_pipeline(affaire, client)


if __name__ == "__main__":
    sys.exit(main())
