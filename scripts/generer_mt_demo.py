"""Génère un mémoire technique complet pour le DCE de démo.

Pipeline :
  1. Lit les 4 PDF du DCE de démo (data/samples/dce-oph-isere/)
  2. Concatène + extraction structurée via Gemini
  3. Génération MT contextualisé via Gemini (sur la bibliothèque MT)
  4. Export DOCX dans data/output/
  5. Dump JSON intermédiaire pour audit
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from i2ao.config import OUTPUT_DIR
from i2ao.docx_export import exporter_mt_docx
from i2ao.extractor import concatener_dce, extraire_analyse_ao
from i2ao.llm import LLMClient
from i2ao.mt_engine import (
    assembler_mt_markdown,
    detecter_variables_non_remplies,
    generer_mt,
)
from i2ao.pdf_parser import detect_type_piece, parse_pdf


def main() -> int:
    dce_dir = PROJECT_ROOT / "data" / "samples" / "dce-oph-isere"
    if not dce_dir.exists():
        print(f"DCE de demo absent : {dce_dir}")
        return 1

    print("=== Etape 1/4 : ingestion des PDF du DCE ===")
    pieces = []
    for pdf in sorted(dce_dir.glob("*.pdf")):
        r = parse_pdf(pdf)
        type_p = detect_type_piece(pdf.name, r.texte_normalise)
        pieces.append((type_p, r.texte_normalise))
        print(f"  {pdf.name:12} -> {type_p:6}  pages={r.nb_pages:2}  chars={len(r.texte_normalise):>6}")

    dce = concatener_dce(pieces)
    print(f"  Total : {len(dce):,} caracteres concatenes")

    client = LLMClient()
    print(f"  Modele LLM : {client.model}")

    print()
    print("=== Etape 2/4 : extraction structuree de l'AO ===")
    analyse = extraire_analyse_ao(client, dce)
    print(f"  -> {len(analyse.exigences)} exigences extraites")
    print(f"  -> {len(analyse.points_attention_majeurs)} points d'attention")
    u = client.last_usage
    print(f"  Usage extraction : prompt={u.prompt_tokens} output={u.output_tokens} thoughts={u.thoughts_tokens}")

    analyse_path = OUTPUT_DIR / "analyse-dce-oph-isere.json"
    analyse_path.write_text(analyse.model_dump_json(indent=2), encoding="utf-8")
    print(f"  Analyse sauvegardee : {analyse_path.relative_to(PROJECT_ROOT)}")

    print()
    print("=== Etape 3/4 : generation du memoire technique ===")
    mt = generer_mt(client, analyse)
    print(f"  -> {len(mt.sections)} sections generees")
    u = client.last_usage
    print(f"  Usage MT : prompt={u.prompt_tokens} output={u.output_tokens} thoughts={u.thoughts_tokens}")

    vars_orphelines = detecter_variables_non_remplies(mt)
    if vars_orphelines:
        print(f"  ATTENTION : {len(vars_orphelines)} sections avec variables non remplies :")
        for pid, vars_list in vars_orphelines.items():
            print(f"    - {pid} : {vars_list}")
    else:
        print("  OK : aucune variable {{...}} non remplie")

    mt_md_path = OUTPUT_DIR / "memoire-technique-oph-isere.md"
    mt_md_path.write_text(assembler_mt_markdown(mt), encoding="utf-8")
    mt_json_path = OUTPUT_DIR / "memoire-technique-oph-isere.json"
    mt_json_path.write_text(mt.model_dump_json(indent=2), encoding="utf-8")
    print(f"  MT en markdown : {mt_md_path.relative_to(PROJECT_ROOT)}")
    print(f"  MT en JSON     : {mt_json_path.relative_to(PROJECT_ROOT)}")

    print()
    print("=== Etape 4/4 : export DOCX ===")
    docx_path = OUTPUT_DIR / "memoire-technique-oph-isere.docx"
    exporter_mt_docx(mt, docx_path)
    size_kb = docx_path.stat().st_size / 1024
    print(f"  DOCX produit : {docx_path.relative_to(PROJECT_ROOT)}  ({size_kb:.1f} KB)")

    print()
    print("=== Pipeline complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
