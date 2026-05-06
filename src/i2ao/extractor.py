"""Extraction structurée d'un DCE via Gemini.

Sortie : un objet AnalyseAO contenant identité du marché + liste exhaustive des
exigences à respecter, classées par catégorie, source et importance.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .llm import LLMClient

CategorieExigence = Literal[
    "piece-a-fournir",
    "critere-jugement",
    "delai",
    "exigence-technique",
    "qualification",
    "reference-experience",
    "moyen",
    "autre",
]

SourcePiece = Literal["RC", "CCAP", "CCTP", "BPU", "DPGF", "AE", "autre"]

ImportanceExigence = Literal["bloquant", "important", "mineur"]


class Exigence(BaseModel):
    categorie: CategorieExigence = Field(
        description="Type d'exigence : piece-a-fournir, critere-jugement, delai, "
        "exigence-technique, qualification, reference-experience, moyen, autre."
    )
    libelle: str = Field(description="Énoncé synthétique en une seule ligne (≤ 120 car).")
    detail: str = Field(
        description="Détail concret en 2 à 4 phrases : ce que le candidat doit faire, "
        "valeurs/seuils précis quand mentionnés."
    )
    source_piece: SourcePiece = Field(description="Pièce du DCE où l'exigence est posée.")
    importance: ImportanceExigence = Field(
        description="bloquant (non-respect = élimination ou inéligibilité), "
        "important (impact significatif sur la note technique), mineur."
    )


class AnalyseAO(BaseModel):
    objet_resume: str = Field(description="Objet du marché en une phrase claire.")
    pouvoir_adjudicateur: str
    type_marche: str = Field(
        description="ordinaire | a-bons-de-commande | accord-cadre | autre"
    )
    materiau_dominant: str = Field(
        description="beton | maconnerie | metal | bois | mixte | non-precise"
    )
    typologie_mission: str = Field(
        description="diag-pur | MOE-confortement | expertise | mission-mixte | autre"
    )
    montant_max_he: str = Field(
        description="Montant maximum HT en euros (ex : '800 000 € HT'), "
        "ou 'non précisé' si absent."
    )
    duree: str = Field(description="Durée du marché (ex : '4 ans max, 1 an + 3 reconductions').")
    date_remise: str = Field(description="Date et heure limite de remise des offres.")
    delai_validite_offre: str = Field(description="Délai de validité des offres.")
    points_attention_majeurs: list[str] = Field(
        description="3 à 6 points d'attention business spécifiques pour le candidat : "
        "spécificités du créneau, exigences inhabituelles, opportunités de différenciation."
    )
    exigences: list[Exigence] = Field(
        description="Liste exhaustive des exigences. Vise 25 à 60 entrées sur un DCE moyen."
    )


_SYSTEM_PROMPT = """Tu es un expert en analyse de DCE de marchés publics français, \
spécialisé dans le créneau **bureau d'études structures pathologie / diagnostic / \
confortement / reprise en sous-œuvre**.

Ton rôle : analyser le DCE fourni et en extraire toutes les exigences structurées \
que le candidat doit absolument respecter pour produire une réponse conforme et \
compétitive.

Pour chaque exigence, qualifie :

**Catégorie :**
- piece-a-fournir : document à inclure dans la réponse (DC1, DC2, attestation, RIB, mémoire, \
BPU, planning…)
- critere-jugement : critère ou sous-critère pondéré de notation des offres
- delai : date ou durée explicite (remise, validité, exécution, réactivité…)
- exigence-technique : exigence sur la méthodologie, le contenu d'un livrable, le respect d'un \
référentiel (Eurocodes, DTU, NF, normes G2…)
- qualification : qualification ou certification professionnelle exigée ou valorisée \
(OPQIBI, RGE, ISO…)
- reference-experience : exigence sur les références chantiers / projets antérieurs
- moyen : exigence sur les moyens humains (CV, équipe) ou matériels
- autre : exigence administrative, financière, contractuelle non couverte ci-dessus

**Source :** le code de la pièce du DCE où l'exigence est posée (RC, CCAP, CCTP, BPU, autre).

**Importance :**
- bloquant : non-respect = élimination, inéligibilité, ou rejet de l'offre
- important : impact significatif sur la note technique ou sur la crédibilité de la réponse
- mineur : exigence formelle, administrative ou de moindre impact

**Règles :**
1. Sois EXHAUSTIF mais pas redondant : ne mentionne pas deux fois la même exigence.
2. Privilégie les exigences ACTIVES (le candidat DOIT faire X) plutôt que des descriptions de contexte.
3. Quand un seuil chiffré est précisé (CA mini, nombre de références, %, montants, délais), \
   reporte-le exactement dans le détail.
4. Distingue clairement les **pièces de candidature** (capacités) des **pièces d'offre** \
   (mémoire, BPU…).
5. Sur les critères de jugement, donne la pondération exacte si elle figure au DCE.
6. Pour les délais d'exécution, distingue le délai global du marché des délais par bon de commande.
7. Les exigences techniques doivent inclure : méthodologie, livrables attendus, référentiels, \
   spécificités métier (RGA, site occupé, amiante, instrumentation, etc.).

Cible 25 à 60 exigences pour un DCE classique.

Pour les **points d'attention majeurs** : 3 à 6 éléments stratégiques pour le candidat \
(opportunités de différenciation, particularités du créneau, exigences inhabituelles).
"""


def extraire_analyse_ao(client: LLMClient, dce_concatene: str) -> AnalyseAO:
    """Lance l'extraction structurée du DCE.

    `dce_concatene` : texte brut concaténé des pièces du DCE, idéalement préfixé
    par leur type (ex : "=== RC ===\n[texte]\n\n=== CCAP ===\n[texte]\n...").
    """
    return client.extract_structured(
        system_prompt=_SYSTEM_PROMPT,
        dce_context=dce_concatene,
        user_message=(
            "Analyse ce DCE et produis l'AnalyseAO complète selon le schéma fourni. "
            "Sois exhaustif sur la liste des exigences."
        ),
        schema=AnalyseAO,
        max_tokens=16000,
        temperature=0.1,
        thinking_budget=4096,
    )


def concatener_dce(pieces: list[tuple[str, str]]) -> str:
    """Concatène les pièces d'un DCE en marquant leur type pour faciliter le sourcing.

    pieces : liste de (type_piece, texte_extrait), ex : [("RC", "..."), ("CCAP", "...")].
    """
    blocs = []
    for type_piece, texte in pieces:
        blocs.append(f"=== PIECE : {type_piece} ===\n\n{texte.strip()}")
    return "\n\n".join(blocs)
