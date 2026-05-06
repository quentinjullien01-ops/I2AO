"""Génère la DPGF (BPU rempli + DQE chiffré) pour le DCE de démo.

Pipeline :
  1. Lit les 4 PDF du DCE de démo
  2. Si analyse-dce-oph-isere.json existe deja, le reutilise. Sinon extraction Gemini.
  3. Generation programme indicatif via Gemini + chiffrage au catalogue
  4. Export XLSX dans data/output/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from i2ao.config import CANDIDAT_NOM, OUTPUT_DIR
from i2ao.dpgf_engine import generer_dpgf
from i2ao.extractor import AnalyseAO, concatener_dce, extraire_analyse_ao
from i2ao.llm import LLMClient
from i2ao.pdf_parser import detect_type_piece, parse_pdf
from i2ao.xlsx_export import exporter_dpgf_xlsx


def main() -> int:
    dce_dir = PROJECT_ROOT / "data" / "samples" / "dce-oph-isere"
    if not dce_dir.exists():
        print(f"DCE de demo absent : {dce_dir}")
        return 1

    print("=== Etape 1/3 : ingestion des PDF du DCE ===")
    pieces = []
    for pdf in sorted(dce_dir.glob("*.pdf")):
        r = parse_pdf(pdf)
        type_p = detect_type_piece(pdf.name, r.texte_normalise)
        pieces.append((type_p, r.texte_normalise))
        print(f"  {pdf.name:12} -> {type_p:6}  pages={r.nb_pages:2}")
    dce = concatener_dce(pieces)
    print(f"  Total : {len(dce):,} caracteres concatenes")

    client = LLMClient()
    print(f"  Modele LLM : {client.model}")

    analyse_path = OUTPUT_DIR / "analyse-dce-oph-isere.json"
    if analyse_path.exists():
        print(f"  -> Reutilise l'analyse existante : {analyse_path.relative_to(PROJECT_ROOT)}")
        analyse = AnalyseAO.model_validate(json.loads(analyse_path.read_text(encoding="utf-8")))
    else:
        print()
        print("=== Etape 2/3 : extraction analyse AO ===")
        analyse = extraire_analyse_ao(client, dce)
        analyse_path.write_text(analyse.model_dump_json(indent=2), encoding="utf-8")
        print(f"  Analyse sauvegardee : {analyse_path.relative_to(PROJECT_ROOT)}")

    print()
    print("=== Etape 3/3 : generation DPGF (programme + chiffrage) ===")
    dpgf = generer_dpgf(client, analyse, dce)
    print(f"  Programme indicatif : {dpgf.description_programme}")
    print(f"  -> {len(dpgf.bpu)} prestations au BPU")
    print(f"  -> {len(dpgf.dqe)} lignes au DQE")
    print(f"  -> Montant DQE total : {dpgf.montant_dqe_he:,.2f} EUR HT")
    if dpgf.lignes_orphelines:
        print(f"  ATTENTION : {len(dpgf.lignes_orphelines)} codes orphelins (non trouves au catalogue) :")
        for c in dpgf.lignes_orphelines:
            print(f"    - {c}")
    u = client.last_usage
    print(f"  Usage Gemini : prompt={u.prompt_tokens} output={u.output_tokens} thoughts={u.thoughts_tokens}")

    dpgf_json_path = OUTPUT_DIR / "dpgf-oph-isere.json"
    dpgf_json_path.write_text(dpgf.model_dump_json(indent=2), encoding="utf-8")
    print(f"  DPGF en JSON : {dpgf_json_path.relative_to(PROJECT_ROOT)}")

    xlsx_path = OUTPUT_DIR / "dpgf-oph-isere.xlsx"
    exporter_dpgf_xlsx(
        dpgf,
        xlsx_path,
        marche_ref="2026-MOE-STRUCT-01",
        candidat=CANDIDAT_NOM,
    )
    size_kb = xlsx_path.stat().st_size / 1024
    print(f"  XLSX produit : {xlsx_path.relative_to(PROJECT_ROOT)}  ({size_kb:.1f} KB)")

    print()
    print("=== Pipeline DPGF complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
