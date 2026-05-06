"""Chargement de la bibliothèque MT (markdown + frontmatter) et du catalogue DPGF (YAML)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter
import yaml
from pydantic import BaseModel, Field

from .config import DPGF_CATALOG_DIR, MT_LIBRARY_DIR, BET_PROFILE_PATH


class ParagrapheMT(BaseModel):
    id: str
    section: str
    sous_section: str | None = None
    ordre: int = 100
    tags: list[str] = Field(default_factory=list)
    adapte_a: list[str] = Field(default_factory=list)
    variables: list[str] = Field(default_factory=list)
    contenu: str
    source_path: str

    @property
    def besoin_variables(self) -> bool:
        return bool(self.variables)


class PrestationDPGF(BaseModel):
    code: str
    libelle: str
    unite: str
    prix_unitaire: float
    categorie: str
    tags: list[str] = Field(default_factory=list)
    note: str | None = None


def load_mt_library() -> list[ParagrapheMT]:
    """Charge tous les paragraphes MT depuis content/mt-library/*.md."""
    paragraphes: list[ParagrapheMT] = []
    if not MT_LIBRARY_DIR.exists():
        return paragraphes

    for path in sorted(MT_LIBRARY_DIR.glob("*.md")):
        post = frontmatter.load(path)
        meta: dict[str, Any] = dict(post.metadata)
        paragraphes.append(
            ParagrapheMT(
                id=str(meta.get("id") or path.stem),
                section=str(meta.get("section") or "Section"),
                sous_section=meta.get("sous_section"),
                ordre=int(meta.get("ordre", 100)),
                tags=list(meta.get("tags") or []),
                adapte_a=list(meta.get("adapte_a") or []),
                variables=list(meta.get("variables") or []),
                contenu=post.content.strip(),
                source_path=str(path.relative_to(MT_LIBRARY_DIR.parent.parent)),
            )
        )
    paragraphes.sort(key=lambda p: (p.ordre, p.id))
    return paragraphes


def load_dpgf_catalog() -> list[PrestationDPGF]:
    """Charge le catalogue de prestations DPGF depuis content/dpgf-catalog/*.yaml."""
    prestations: list[PrestationDPGF] = []
    if not DPGF_CATALOG_DIR.exists():
        return prestations

    for path in sorted(DPGF_CATALOG_DIR.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for entry in data.get("prestations", []):
            prestations.append(PrestationDPGF(**entry))
    return prestations


def load_bet_profile() -> str:
    """Charge le profil entreprise (références, équipe, certifs)."""
    if not BET_PROFILE_PATH.exists():
        return ""
    return BET_PROFILE_PATH.read_text(encoding="utf-8")
