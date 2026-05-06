"""Score de couverture du mémoire technique vis-à-vis des exigences extraites.

Pour chaque exigence bloquante du DCE, on demande à Gemini d'évaluer si le MT
la couvre, et on calcule un score de complétude. Le rapport identifie aussi
les exigences applicables au MT mais non traitées — c'est l'angle de
différenciation produit ("l'outil vérifie sa propre conformité").
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .extractor import AnalyseAO, Exigence
from .llm import LLMClient
from .mt_engine import MemoireTechniqueGenere

StatutCouverture = Literal["couverte", "partiellement-couverte", "non-couverte", "non-applicable"]


class CouvertureExigence(BaseModel):
    exigence_libelle: str = Field(description="Libellé exact de l'exigence évaluée.")
    categorie: str = Field(description="Catégorie de l'exigence (recopiée).")
    importance: str = Field(description="Importance de l'exigence (recopiée).")
    statut: StatutCouverture = Field(
        description="couverte (clairement traitée par le MT), "
        "partiellement-couverte (mention insuffisante, à compléter), "
        "non-couverte (absente du MT alors que pertinente), "
        "non-applicable (cette exigence se traite ailleurs : DC1/DC2, attestation, BPU…)."
    )
    section_mt_id: str | None = Field(
        default=None,
        description="paragraphe_id de la section MT qui traite cette exigence (None si non couverte ou n/a).",
    )
    extrait_mt: str | None = Field(
        default=None,
        description="Extrait du MT (≤ 60 mots) qui couvre l'exigence (None si non couverte ou n/a).",
    )
    commentaire: str = Field(
        description="Justification courte (≤ 30 mots) — ce qui couvre, ou ce qui manque."
    )


class RapportCouverture(BaseModel):
    nb_total_evaluees: int = Field(description="Nombre total d'exigences évaluées.")
    nb_couvertes: int
    nb_partiellement_couvertes: int
    nb_non_couvertes: int
    nb_non_applicables: int
    score_pct: float = Field(
        description="Score : (couvertes + 0.5 * partiellement-couvertes) / (applicables) × 100. "
        "Les non-applicables sont exclues du dénominateur."
    )
    synthese: str = Field(
        description="Synthèse du rapport en 2-3 phrases : niveau global de couverture + "
        "exigences non couvertes les plus critiques."
    )
    details: list[CouvertureExigence]


_SYSTEM_PROMPT = """Tu évalues la couverture d'un **mémoire technique** vis-à-vis des **exigences** \
extraites d'un AO public, dans le cadre d'un BET structures spécialisé en pathologie / \
diagnostic / confortement.

Pour chaque exigence fournie, détermine si le MT la couvre, en respectant les règles suivantes.

**Quel statut attribuer ?**

- `couverte` : le MT traite l'exigence de façon claire et explicite. Tu dois identifier la \
section MT qui la traite (`section_mt_id`) et fournir un extrait (`extrait_mt`, ≤ 60 mots).
- `partiellement-couverte` : le MT mentionne le sujet mais sans le développer, ou ne traite \
qu'une partie de l'exigence. Identifie la section et l'extrait, et explique en commentaire \
ce qui manque.
- `non-couverte` : l'exigence est applicable au MT (cf. règle ci-dessous) mais n'y est pas \
traitée. Pas de section_mt_id ni d'extrait. Explique en commentaire ce qui manque.
- `non-applicable` : l'exigence ne se traite PAS dans le mémoire technique mais dans une \
autre pièce de la candidature ou de l'offre. C'est notamment le cas pour :
  - `piece-a-fournir` : les pièces administratives (DC1, DC2, attestation d'assurance, RIB, \
    actes d'engagement, formulaires) — sauf si l'exigence porte sur le MT lui-même \
    (« mémoire technique de 30 pages max », « plan / contenu attendu du MT ») où c'est \
    la structure du MT qui couvre.
  - `delai` administratif (validité offre, délai de remise) — c'est l'AE qui couvre.
  - `autre` lorsqu'il s'agit d'une clause administrative pure.

**Quelles catégories sont APPLICABLES au MT ?**

- `exigence-technique` : presque toujours applicable, le MT doit décrire la méthodologie.
- `qualification` : applicable, le MT doit présenter les qualifs détenues.
- `reference-experience` : applicable, le MT doit présenter les références.
- `moyen` : applicable, le MT doit décrire les moyens humains/matériels.
- `critere-jugement` : applicable si c'est un critère technique qui sera évalué sur le MT.
- `delai` : applicable si c'est un délai d'**exécution** ou un engagement de réactivité \
  que le candidat doit prendre dans son MT.

**Règles de qualité :**

1. Sois CRITIQUE et HONNÊTE : ne marque pas "couverte" si la mention est superficielle.
2. Identifie correctement le `section_mt_id` (par ex `mt-04-methodologie-moe-confortement`).
3. L'extrait_mt doit être un VRAI extrait (citation), pas un résumé.
4. Le commentaire est court et factuel : "couvre la méthodologie phase par phase" ou \
   "manque la mention explicite de la coordination locataires en logement habité".
"""


def evaluer_couverture(
    client: LLMClient,
    analyse: AnalyseAO,
    mt: MemoireTechniqueGenere,
    importance_min: str = "important",
) -> RapportCouverture:
    """Évalue la couverture du MT sur les exigences d'importance >= seuil.

    Par défaut on évalue les exigences `bloquant` et `important` (les `mineures`
    sont exclues pour ne pas diluer le score).
    """
    importances_retenues: set[str] = set()
    if importance_min == "mineur":
        importances_retenues = {"bloquant", "important", "mineur"}
    elif importance_min == "important":
        importances_retenues = {"bloquant", "important"}
    else:
        importances_retenues = {"bloquant"}

    exigences_a_evaluer: list[Exigence] = [
        e for e in analyse.exigences if e.importance in importances_retenues
    ]

    user_prompt = _build_prompt(exigences_a_evaluer, mt)

    rapport = client.extract_structured(
        system_prompt=_SYSTEM_PROMPT,
        dce_context=None,
        user_message=user_prompt,
        schema=RapportCouverture,
        max_tokens=16000,
        temperature=0.1,
        thinking_budget=2048,
    )

    # Recalcul cohérent côté Python pour fiabilité (le LLM peut rater l'arithmétique).
    return _consolider_rapport(rapport)


def _build_prompt(exigences: list[Exigence], mt: MemoireTechniqueGenere) -> str:
    parts = ["## Mémoire technique à évaluer\n"]
    for s in mt.sections:
        parts.append(f"### Section [{s.paragraphe_id}] — {s.titre}")
        if s.sous_titre:
            parts.append(f"_{s.sous_titre}_")
        parts.append(s.contenu_md.strip())
        parts.append("")

    parts.append(f"## Exigences à évaluer ({len(exigences)})\n")
    for i, e in enumerate(exigences, 1):
        parts.append(
            f"{i}. [{e.importance}/{e.categorie}/{e.source_piece}] **{e.libelle}**"
        )
        if e.detail:
            parts.append(f"   Détail : {e.detail}")
        parts.append("")

    parts.append(
        "Évalue chaque exigence dans l'ordre. Produis le rapport complet avec un détail "
        "par exigence."
    )
    return "\n".join(parts)


def _consolider_rapport(rapport: RapportCouverture) -> RapportCouverture:
    """Recalcule les compteurs et le score à partir du détail (fiabilise vs hallucination)."""
    couvertes = sum(1 for d in rapport.details if d.statut == "couverte")
    partielles = sum(1 for d in rapport.details if d.statut == "partiellement-couverte")
    non_couvertes = sum(1 for d in rapport.details if d.statut == "non-couverte")
    non_applicables = sum(1 for d in rapport.details if d.statut == "non-applicable")
    total = len(rapport.details)
    applicables = total - non_applicables
    if applicables > 0:
        score = round((couvertes + 0.5 * partielles) / applicables * 100, 1)
    else:
        score = 0.0
    return RapportCouverture(
        nb_total_evaluees=total,
        nb_couvertes=couvertes,
        nb_partiellement_couvertes=partielles,
        nb_non_couvertes=non_couvertes,
        nb_non_applicables=non_applicables,
        score_pct=score,
        synthese=rapport.synthese,
        details=rapport.details,
    )
