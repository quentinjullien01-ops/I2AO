"""Extraction du texte des pièces PDF d'un DCE.

Stratégie en cascade :
  1. pdfplumber (meilleure préservation du layout sur PDF tabulaires type DPGF/BPU)
  2. pymupdf en fallback (PDF compressés en flate atypique)
  3. OCR via pytesseract si tout reste vide (PDF scannés)
  4. Sinon : marquage "scanné probable" + avertissement clair

L'OCR nécessite Tesseract installé sur le système (binaire), avec idéalement le
pack de langue française (`fra`). Sur Windows :
https://github.com/UB-Mannheim/tesseract/wiki
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # pymupdf
import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class TextePDF:
    nom_fichier: str
    nb_pages: int
    texte: str
    pages: list[str]
    methode: str  # "pdfplumber" | "pymupdf" | "vide-probable-scanne"
    est_probablement_scanne: bool = False
    avertissements: list[str] = field(default_factory=list)

    @property
    def texte_normalise(self) -> str:
        return _normalize(self.texte)


def parse_pdf(
    source: Path | bytes,
    nom_fichier: str | None = None,
    autoriser_ocr: bool = True,
) -> TextePDF:
    """Extrait le texte d'un PDF depuis un chemin ou des bytes.

    Stratégie en cascade : pdfplumber → pymupdf → OCR Tesseract (si activé) →
    sinon marquage "scanné probable" + avertissement.
    """
    if isinstance(source, Path):
        nom = nom_fichier or source.name
        data = source.read_bytes()
    else:
        nom = nom_fichier or "document.pdf"
        data = source

    avertissements: list[str] = []

    pages = _extract_with_pdfplumber(data)
    methode = "pdfplumber"

    if _is_quasi_empty(pages):
        pages_pmu = _extract_with_pymupdf(data)
        if not _is_quasi_empty(pages_pmu):
            pages = pages_pmu
            methode = "pymupdf"
        elif autoriser_ocr and is_ocr_available():
            pages_ocr, ocr_warning = _extract_with_ocr(data)
            if pages_ocr and not _is_quasi_empty(pages_ocr):
                pages = pages_ocr
                methode = "ocr-tesseract"
                avertissements.append(
                    f"'{nom}' a été extrait par OCR Tesseract (PDF scanné détecté). "
                    "L'extraction OCR a un taux d'erreur supérieur à l'extraction texte natif ; "
                    "vérifie les chiffres et noms propres avant de t'engager."
                )
            else:
                pages = pages_pmu if pages_pmu else pages
                methode = "vide-probable-scanne"
                if ocr_warning:
                    avertissements.append(ocr_warning)
                else:
                    avertissements.append(
                        f"Aucun texte extractible depuis '{nom}', y compris par OCR. "
                        "Le PDF n'est probablement pas exploitable."
                    )
        else:
            pages = pages_pmu if pages_pmu else pages
            methode = "vide-probable-scanne"
            if not is_ocr_available():
                avertissements.append(
                    f"Aucun texte extractible depuis '{nom}'. Le document est probablement "
                    "un scan d'image. Pour le traiter, installer Tesseract OCR : "
                    "https://github.com/UB-Mannheim/tesseract/wiki "
                    "(et idéalement le pack de langue 'fra')."
                )
            else:
                avertissements.append(
                    f"Aucun texte extractible depuis '{nom}'. PDF probablement scanné."
                )

    return TextePDF(
        nom_fichier=nom,
        nb_pages=len(pages),
        texte="\n\n".join(f"--- Page {i + 1} ---\n{p}" for i, p in enumerate(pages)),
        pages=pages,
        methode=methode,
        est_probablement_scanne=(methode == "vide-probable-scanne"),
        avertissements=avertissements,
    )


def _extract_with_pdfplumber(data: bytes) -> list[str]:
    out: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            out.append(txt.strip())
    return out


def _extract_with_pymupdf(data: bytes) -> list[str]:
    out: list[str] = []
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        for page in doc:
            out.append(page.get_text("text").strip())
    finally:
        doc.close()
    return out


def is_ocr_available() -> bool:
    """Vérifie si Tesseract OCR est utilisable (binaire + wrapper Python)."""
    try:
        import pytesseract
    except ImportError:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except (pytesseract.TesseractNotFoundError, Exception):
        return False


def _extract_with_ocr(data: bytes, langue: str = "fra+eng") -> tuple[list[str], str | None]:
    """OCR via Tesseract sur chaque page rendue en image 300 DPI.

    Retourne (pages_textuelles, avertissement_eventuel).
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return [], (
            "OCR demandé mais le module pytesseract n'est pas installé. "
            "Installer via : pip install pytesseract Pillow"
        )

    pages_text: list[str] = []
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        # Si pack 'fra' indispo, fallback sur 'eng'
        try:
            available_langs = pytesseract.get_languages()
        except Exception:
            available_langs = ["eng"]
        if "fra" not in available_langs:
            langue = "eng"
            logger.warning(
                "Pack de langue Tesseract 'fra' non installé, OCR en anglais "
                "(qualité dégradée sur du texte français)."
            )

        for page in doc:
            mat = fitz.Matrix(3.0, 3.0)  # ~300 DPI
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
            try:
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                text = pytesseract.image_to_string(img, lang=langue)
            except pytesseract.TesseractNotFoundError:
                return [], (
                    "Tesseract n'est pas installé sur ce poste ou n'est pas dans le PATH. "
                    "Voir https://github.com/UB-Mannheim/tesseract/wiki pour Windows."
                )
            except Exception as e:
                logger.warning("OCR échoué sur une page : %s", e)
                text = ""
            pages_text.append(text.strip())
    finally:
        doc.close()
    return pages_text, None


def _is_quasi_empty(pages: list[str]) -> bool:
    if not pages:
        return True
    total_chars = sum(len(p) for p in pages)
    return total_chars < max(50, 20 * len(pages))


_WS_RE = re.compile(r"[ \t]+")
_NL_RE = re.compile(r"\n{3,}")


def _normalize(text: str) -> str:
    text = _WS_RE.sub(" ", text)
    text = _NL_RE.sub("\n\n", text)
    return text.strip()


_PIECE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("RC", re.compile(r"r[eè]glement[\s_\-]+(de[\s_\-]+(la[\s_\-]+)?)?consultation|\brc[\s_\-]|^rc[\s_\-\.]|[\s_\-]rc[\s_\-\.]", re.IGNORECASE)),
    ("CCAP", re.compile(r"c\.?c\.?a\.?p\.?|cahier\s+des\s+clauses\s+administratives", re.IGNORECASE)),
    ("CCTP", re.compile(r"c\.?c\.?t\.?p\.?|cahier\s+des\s+clauses\s+techniques", re.IGNORECASE)),
    ("BPU", re.compile(r"(?<![a-zA-Z0-9])bpu(?![a-zA-Z0-9])|bordereau\s+des\s+prix\s+unitaires", re.IGNORECASE)),
    ("DPGF", re.compile(r"(?<![a-zA-Z0-9])dpgf(?![a-zA-Z0-9])|d[eé]composition\s+du\s+prix\s+global", re.IGNORECASE)),
    ("DQE", re.compile(r"(?<![a-zA-Z0-9])dqe(?![a-zA-Z0-9])|d[eé]tail\s+quantitatif\s+estimatif", re.IGNORECASE)),
    ("AE", re.compile(r"acte[\s_\-]+(d.?)?engagement|(?<![a-zA-Z0-9])ae(?![a-zA-Z0-9])", re.IGNORECASE)),
]


def detect_type_piece(nom_fichier: str, texte_extrait: str = "") -> str:
    """Devine le type de pièce DCE.

    On teste le nom de fichier en priorité (forte confiance), puis seulement
    on retombe sur le contenu : un BPU peut citer le CCAP en référence croisée
    sans pour autant être un CCAP.
    """
    for code, pattern in _PIECE_PATTERNS:
        if pattern.search(nom_fichier):
            return code
    if texte_extrait:
        # Sur le contenu, on regarde la 1ère page (titre + en-tête) en priorité.
        head = texte_extrait[:1500]
        for code, pattern in _PIECE_PATTERNS:
            if pattern.search(head):
                return code
    return "autre"
