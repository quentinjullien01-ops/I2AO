"""Chargement de la bibliothèque MT (markdown + frontmatter) et du catalogue DPGF (YAML)."""

from __future__ import annotations

from typing import Any

import frontmatter
import yaml
from pydantic import BaseModel, Field

from .config import (
    BET_PROFILE_PATH,
    DPGF_CATALOG_DIR,
    MT_LIBRARY_DIR,
    chemins_profil,
)


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


def load_mt_library(profil: str | None = None) -> list[ParagrapheMT]:
    """Charge tous les paragraphes MT depuis le profil actif (ou explicite).

    Si `profil` est None, utilise le chemin par défaut (PROFIL_ACTIF_DEFAUT).
    """
    mt_dir = chemins_profil(profil)["mt_library"] if profil else MT_LIBRARY_DIR

    paragraphes: list[ParagrapheMT] = []
    if not mt_dir.exists():
        return paragraphes

    for path in sorted(mt_dir.glob("*.md")):
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
                source_path=str(path.relative_to(mt_dir.parents[2])),
            )
        )
    paragraphes.sort(key=lambda p: (p.ordre, p.id))
    return paragraphes


def load_dpgf_catalog(profil: str | None = None) -> list[PrestationDPGF]:
    """Charge le catalogue de prestations DPGF du profil actif (ou explicite)."""
    dpgf_dir = chemins_profil(profil)["dpgf_catalog"] if profil else DPGF_CATALOG_DIR

    prestations: list[PrestationDPGF] = []
    if not dpgf_dir.exists():
        return prestations

    for path in sorted(dpgf_dir.glob("*.yaml")):
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for entry in data.get("prestations", []):
                try:
                    prestations.append(PrestationDPGF(**entry))
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(
                        "Entrée DPGF invalide dans %s : %s — ignorée", path.name, e
                    )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "Impossible de lire le catalogue DPGF %s : %s — ignoré", path.name, e
            )
    return prestations


def load_bet_profile(profil: str | None = None) -> str:
    """Charge le profil entreprise (références, équipe, certifs) du profil actif."""
    profile_path = chemins_profil(profil)["bet_profile"] if profil else BET_PROFILE_PATH
    if not profile_path.exists():
        return ""
    return profile_path.read_text(encoding="utf-8")
