"""Génère les PDF du DCE fictif de démo à partir des sources markdown.

Usage :
    .venv/Scripts/python.exe scripts/generate_demo_dce.py

Lit data/samples/source/dce-oph-isere/*.md et écrit data/samples/dce-oph-isere/*.pdf.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import HRFlowable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "data" / "samples" / "source"
OUT_ROOT = PROJECT_ROOT / "data" / "samples"

PIECE_TITLES = {
    "RC": "Règlement de la Consultation",
    "CCAP": "CCAP — Cahier des Clauses Administratives Particulières",
    "CCTP": "CCTP — Cahier des Clauses Techniques Particulières",
    "BPU": "Bordereau des Prix Unitaires",
    "DPGF": "Décomposition du Prix Global et Forfaitaire",
    "AE": "Acte d'Engagement",
}

# Métadonnées par projet : référence marché + pouvoir adjudicateur affichés en en-tête.
PROJECT_METADATA = {
    "dce-oph-isere": {
        "marche_ref": "Marché 2026-MOE-STRUCT-01",
        "entite": "OPH des Vallées de l'Isère",
    },
    "dce-confortement-saint-marcellin": {
        "marche_ref": "Marché 2026-MAPA-MOE-04",
        "entite": "Commune de Saint-Marcellin",
    },
}

# Globals utilisées par les fonctions d'en-tête (set par main pour chaque projet).
MARCHE_REF = ""
ENTITE = ""


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    styles: dict[str, ParagraphStyle] = {}
    styles["Cover"] = ParagraphStyle(
        "Cover",
        parent=base["Title"],
        fontName="Times-Bold",
        fontSize=22,
        leading=28,
        alignment=1,
        spaceAfter=20,
    )
    styles["CoverSub"] = ParagraphStyle(
        "CoverSub",
        parent=base["Normal"],
        fontName="Times-Roman",
        fontSize=12,
        leading=16,
        alignment=1,
        spaceAfter=8,
    )
    styles["H1"] = ParagraphStyle(
        "H1",
        parent=base["Heading1"],
        fontName="Times-Bold",
        fontSize=18,
        leading=22,
        spaceBefore=24,
        spaceAfter=12,
        textColor=colors.HexColor("#1a3d6e"),
    )
    styles["H2"] = ParagraphStyle(
        "H2",
        parent=base["Heading2"],
        fontName="Times-Bold",
        fontSize=13,
        leading=17,
        spaceBefore=18,
        spaceAfter=8,
        textColor=colors.HexColor("#1a3d6e"),
    )
    styles["H3"] = ParagraphStyle(
        "H3",
        parent=base["Heading3"],
        fontName="Times-Bold",
        fontSize=11,
        leading=14,
        spaceBefore=10,
        spaceAfter=4,
        textColor=colors.HexColor("#333333"),
    )
    styles["Body"] = ParagraphStyle(
        "Body",
        parent=base["BodyText"],
        fontName="Times-Roman",
        fontSize=10.5,
        leading=14,
        spaceAfter=6,
        alignment=4,  # justify
    )
    styles["Bullet"] = ParagraphStyle(
        "Bullet",
        parent=base["BodyText"],
        fontName="Times-Roman",
        fontSize=10.5,
        leading=14,
        leftIndent=18,
        bulletIndent=6,
        spaceAfter=3,
        alignment=4,
    )
    return styles


_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITAL_RE = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def inline_md_to_html(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = _BOLD_RE.sub(r"<b>\1</b>", text)
    text = _ITAL_RE.sub(r"<i>\1</i>", text)
    text = _LINK_RE.sub(r'<u>\1</u>', text)
    return text


def is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and "|" in s[1:-1]


def parse_table_block(lines: list[str], i: int) -> tuple[list[list[str]], int]:
    """Lit un bloc de table markdown à partir de l'index i. Retourne (rows, next_i)."""
    rows: list[list[str]] = []
    while i < len(lines) and is_table_row(lines[i]):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if all(re.match(r"^:?-+:?$", c) for c in cells if c):
            i += 1
            continue
        rows.append(cells)
        i += 1
    return rows, i


def build_flowables(md_text: str, styles: dict[str, ParagraphStyle]) -> list:
    flow: list = []
    lines = md_text.splitlines()
    i = 0
    in_first_h1 = True
    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            i += 1
            continue

        if line.strip() == "---":
            flow.append(Spacer(1, 6))
            flow.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#888888")))
            flow.append(Spacer(1, 8))
            i += 1
            continue

        if line.startswith("# "):
            text = inline_md_to_html(line[2:].strip())
            if in_first_h1:
                flow.append(Spacer(1, 4 * cm))
                flow.append(Paragraph(MARCHE_REF, styles["CoverSub"]))
                flow.append(Spacer(1, 0.4 * cm))
                flow.append(Paragraph(text, styles["Cover"]))
                flow.append(HRFlowable(width="60%", thickness=1, color=colors.HexColor("#1a3d6e"), hAlign="CENTER"))
                flow.append(Spacer(1, 0.6 * cm))
                flow.append(Paragraph(ENTITE, styles["CoverSub"]))
                in_first_h1 = False
            else:
                flow.append(PageBreak())
                flow.append(Paragraph(text, styles["H1"]))
            i += 1
            continue

        if line.startswith("## "):
            text = inline_md_to_html(line[3:].strip())
            flow.append(Paragraph(text, styles["H1"]))
            i += 1
            continue

        if line.startswith("### "):
            text = inline_md_to_html(line[4:].strip())
            flow.append(Paragraph(text, styles["H2"]))
            i += 1
            continue

        if line.startswith("#### "):
            text = inline_md_to_html(line[5:].strip())
            flow.append(Paragraph(text, styles["H3"]))
            i += 1
            continue

        if is_table_row(line):
            rows, next_i = parse_table_block(lines, i)
            if rows:
                flow.append(_render_table(rows, styles))
            i = next_i
            continue

        if line.lstrip().startswith(("- ", "* ")):
            bullet_lines: list[str] = []
            while i < len(lines) and lines[i].lstrip().startswith(("- ", "* ")):
                content = lines[i].lstrip()[2:].strip()
                bullet_lines.append(content)
                i += 1
            for bl in bullet_lines:
                flow.append(Paragraph(inline_md_to_html(bl), styles["Bullet"], bulletText="•"))
            continue

        if re.match(r"^\d+\.\s", line.lstrip()):
            num_lines: list[tuple[str, str]] = []
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i].lstrip()):
                m = re.match(r"^(\d+)\.\s+(.*)$", lines[i].lstrip())
                if m:
                    num_lines.append((m.group(1), m.group(2).strip()))
                i += 1
            for num, content in num_lines:
                flow.append(
                    Paragraph(
                        inline_md_to_html(content),
                        styles["Bullet"],
                        bulletText=f"{num}.",
                    )
                )
            continue

        # Paragraphe : agréger les lignes consécutives non vides non spéciales
        para_lines: list[str] = []
        while i < len(lines):
            ln = lines[i].rstrip()
            if not ln.strip():
                break
            if (
                ln.startswith(("# ", "## ", "### ", "#### ", "- ", "* "))
                or ln.strip() == "---"
                or is_table_row(ln)
                or re.match(r"^\d+\.\s", ln.lstrip())
            ):
                break
            para_lines.append(ln)
            i += 1
        text = inline_md_to_html(" ".join(p.strip() for p in para_lines))
        flow.append(Paragraph(text, styles["Body"]))

    return flow


def _render_table(rows: list[list[str]], styles: dict[str, ParagraphStyle]) -> Table:
    cell_style = ParagraphStyle(
        "Cell",
        parent=styles["Body"],
        fontSize=9.5,
        leading=12,
        alignment=0,
        spaceAfter=0,
    )
    header_style = ParagraphStyle(
        "CellHeader",
        parent=cell_style,
        fontName="Times-Bold",
        textColor=colors.white,
    )
    data: list[list] = []
    for r_idx, row in enumerate(rows):
        rendered = [
            Paragraph(inline_md_to_html(cell), header_style if r_idx == 0 else cell_style)
            for cell in row
        ]
        data.append(rendered)

    n_cols = max(len(r) for r in data)
    page_width = A4[0] - 5 * cm
    col_widths = [page_width / n_cols] * n_cols
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3d6e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#888888")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6fa")]),
            ]
        )
    )
    return table


def make_page_decorator(piece_title: str):
    def draw_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Times-Italic", 8.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(2.5 * cm, A4[1] - 1.2 * cm, f"{MARCHE_REF}  —  {piece_title}")
        canvas.drawRightString(A4[0] - 2.5 * cm, A4[1] - 1.2 * cm, ENTITE)
        canvas.setStrokeColor(colors.HexColor("#cccccc"))
        canvas.setLineWidth(0.4)
        canvas.line(2.5 * cm, A4[1] - 1.4 * cm, A4[0] - 2.5 * cm, A4[1] - 1.4 * cm)
        canvas.setFont("Times-Roman", 8.5)
        canvas.drawCentredString(A4[0] / 2, 1.2 * cm, f"Page {doc.page}")
        canvas.restoreState()

    return draw_page


def render_pdf(md_path: Path, out_path: Path, piece_title: str) -> None:
    md_text = md_path.read_text(encoding="utf-8")
    styles = build_styles()
    story = build_flowables(md_text, styles)

    doc = BaseDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
        title=piece_title,
        author=ENTITE,
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="body",
    )
    template = PageTemplate(id="main", frames=[frame], onPage=make_page_decorator(piece_title))
    doc.addPageTemplates([template])
    doc.build(story)


def piece_code_from_filename(path: Path) -> str:
    return path.stem.upper()


def main() -> int:
    global MARCHE_REF, ENTITE

    if not SRC_ROOT.exists():
        print(f"Source absente : {SRC_ROOT}")
        return 1

    project_dirs = [d for d in sorted(SRC_ROOT.iterdir()) if d.is_dir()]
    if not project_dirs:
        print(f"Aucun projet sous {SRC_ROOT}")
        return 1

    total = 0
    for project_dir in project_dirs:
        slug = project_dir.name
        meta = PROJECT_METADATA.get(slug, {})
        MARCHE_REF = meta.get("marche_ref", f"Marché {slug}")
        ENTITE = meta.get("entite", slug)

        out_dir = OUT_ROOT / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        md_files = sorted(project_dir.glob("*.md"))
        if not md_files:
            print(f"  ! aucun .md dans {project_dir.relative_to(PROJECT_ROOT)}")
            continue

        print(f"\n=== {slug} ({ENTITE}) ===")
        for md_path in md_files:
            code = piece_code_from_filename(md_path)
            title = PIECE_TITLES.get(code, code)
            out = out_dir / f"{code}.pdf"
            render_pdf(md_path, out, title)
            size_kb = out.stat().st_size / 1024
            print(f"  [OK] {out.relative_to(PROJECT_ROOT)}  ({size_kb:.1f} KB)")
            total += 1

    print(f"\n-> {total} fichier(s) genere(s) au total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
