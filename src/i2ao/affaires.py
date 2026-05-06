"""Gestion des affaires (AO en cours) sur disque.

Chaque affaire = un dossier sous data/affaires/<slug>/
  - pieces/         : PDFs déposés
  - meta.json       : métadonnées (slug, nom, date_creation, etc.)
  - analyse.json    : analyse de l'AO (extraction)
  - mt.json/.docx   : mémoire technique généré
  - dpgf.json/.xlsx : DPGF générée
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import DATA_DIR, SAMPLES_DIR

AFFAIRES_DIR = DATA_DIR / "affaires"


@dataclass
class Affaire:
    slug: str
    nom: str
    date_creation: str
    dossier: Path

    @property
    def pieces_dir(self) -> Path:
        return self.dossier / "pieces"

    @property
    def analyse_path(self) -> Path:
        return self.dossier / "analyse.json"

    @property
    def mt_json_path(self) -> Path:
        return self.dossier / "mt.json"

    @property
    def mt_docx_path(self) -> Path:
        return self.dossier / "mt.docx"

    @property
    def dpgf_json_path(self) -> Path:
        return self.dossier / "dpgf.json"

    @property
    def dpgf_xlsx_path(self) -> Path:
        return self.dossier / "dpgf.xlsx"

    @property
    def couverture_path(self) -> Path:
        return self.dossier / "couverture.json"

    @property
    def synthese_json_path(self) -> Path:
        return self.dossier / "synthese.json"

    @property
    def synthese_docx_path(self) -> Path:
        return self.dossier / "synthese.docx"

    @property
    def lettre_json_path(self) -> Path:
        return self.dossier / "lettre.json"

    @property
    def lettre_docx_path(self) -> Path:
        return self.dossier / "lettre.docx"

    @property
    def pack_zip_path(self) -> Path:
        return self.dossier / f"pack-candidature-{self.slug}.zip"

    @property
    def meta_path(self) -> Path:
        return self.dossier / "meta.json"

    def has_pieces(self) -> bool:
        return self.pieces_dir.exists() and any(self.pieces_dir.glob("*.pdf"))

    def has_analyse(self) -> bool:
        return self.analyse_path.exists()

    def has_mt(self) -> bool:
        return self.mt_json_path.exists()

    def has_dpgf(self) -> bool:
        return self.dpgf_json_path.exists()

    def has_couverture(self) -> bool:
        return self.couverture_path.exists()

    def has_synthese(self) -> bool:
        return self.synthese_json_path.exists()


def _slugify(nom: str) -> str:
    s = nom.lower()
    s = re.sub(r"[éèêë]", "e", s)
    s = re.sub(r"[àâä]", "a", s)
    s = re.sub(r"[ùûü]", "u", s)
    s = re.sub(r"[îï]", "i", s)
    s = re.sub(r"[ôö]", "o", s)
    s = re.sub(r"[ç]", "c", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "ao"


def lister_affaires() -> list[Affaire]:
    """Renvoie la liste des affaires existantes triée par date de création décroissante."""
    AFFAIRES_DIR.mkdir(parents=True, exist_ok=True)
    affaires: list[Affaire] = []
    for dossier in sorted(AFFAIRES_DIR.iterdir()):
        if not dossier.is_dir():
            continue
        meta_path = dossier / "meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        affaires.append(
            Affaire(
                slug=meta.get("slug", dossier.name),
                nom=meta.get("nom", dossier.name),
                date_creation=meta.get("date_creation", ""),
                dossier=dossier,
            )
        )
    affaires.sort(key=lambda a: a.date_creation, reverse=True)
    return affaires


def get_affaire(slug: str) -> Affaire | None:
    for a in lister_affaires():
        if a.slug == slug:
            return a
    return None


def creer_affaire(nom: str) -> Affaire:
    slug = _slugify(nom)
    AFFAIRES_DIR.mkdir(parents=True, exist_ok=True)
    dossier = AFFAIRES_DIR / slug
    if dossier.exists():
        # Suffixe pour eviter collision
        i = 2
        while (AFFAIRES_DIR / f"{slug}-{i}").exists():
            i += 1
        slug = f"{slug}-{i}"
        dossier = AFFAIRES_DIR / slug
    dossier.mkdir(parents=True)
    (dossier / "pieces").mkdir()
    meta = {
        "slug": slug,
        "nom": nom,
        "date_creation": datetime.now().isoformat(timespec="seconds"),
    }
    (dossier / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return Affaire(
        slug=slug,
        nom=nom,
        date_creation=meta["date_creation"],
        dossier=dossier,
    )


def supprimer_affaire(slug: str) -> bool:
    a = get_affaire(slug)
    if not a:
        return False
    shutil.rmtree(a.dossier)
    return True


def ajouter_piece(affaire: Affaire, nom_fichier: str, contenu: bytes) -> Path:
    affaire.pieces_dir.mkdir(parents=True, exist_ok=True)
    target = affaire.pieces_dir / nom_fichier
    target.write_bytes(contenu)
    return target


_DEMOS = [
    {
        "slug": "demo-oph-vallees-isere",
        "nom": "OPH des Vallées de l'Isère — diag + MOE confortement (à bons de commande)",
        "source_subdir": "dce-oph-isere",
    },
    {
        "slug": "demo-confortement-saint-marcellin",
        "nom": "Commune de Saint-Marcellin — MOE confortement salle des fêtes (MAPA forfait)",
        "source_subdir": "dce-confortement-saint-marcellin",
    },
]


def _initialiser_une_demo(slug: str, nom: str, source_subdir: str) -> Affaire | None:
    AFFAIRES_DIR.mkdir(parents=True, exist_ok=True)
    dossier = AFFAIRES_DIR / slug
    if dossier.exists():
        return get_affaire(slug)

    source = SAMPLES_DIR / source_subdir
    if not source.exists():
        return None

    dossier.mkdir(parents=True)
    pieces = dossier / "pieces"
    pieces.mkdir()
    for pdf in source.glob("*.pdf"):
        shutil.copy2(pdf, pieces / pdf.name)

    meta = {
        "slug": slug,
        "nom": nom,
        "date_creation": datetime.now().isoformat(timespec="seconds"),
        "demo": True,
    }
    (dossier / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return get_affaire(slug)


def initialiser_demo_si_absente() -> Affaire | None:
    """Crée les affaires de démo (si absentes) et renvoie la première (par défaut OPH)."""
    premiere: Affaire | None = None
    for d in _DEMOS:
        a = _initialiser_une_demo(d["slug"], d["nom"], d["source_subdir"])
        if premiere is None and a is not None:
            premiere = a
    return premiere
