"""Moteur d'assemblage du mémoire technique.

Stratégie : on envoie en un seul appel Gemini la bibliothèque MT complète, le
profil entreprise et l'analyse de l'AO. Gemini contextualise chaque paragraphe
(remplissage des {{variables}}, adaptation au cas d'espèce) et nous retourne la
liste des sections en JSON. Plus rapide et cohérent qu'un appel par paragraphe.
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, Field

from .content_loader import ParagrapheMT, load_mt_library, load_bet_profile
from .extractor import AnalyseAO
from .llm import LLMClient


class SectionMT(BaseModel):
    paragraphe_id: str = Field(description="Identifiant du paragraphe source dans la bibliothèque MT.")
    titre: str = Field(description="Titre de la section (H1) dans le mémoire technique.")
    sous_titre: str | None = Field(
        default=None, description="Sous-titre éventuel (H2) pour les sous-sections."
    )
    contenu_md: str = Field(
        description="Contenu de la section en markdown, avec toutes les variables remplies "
        "ou les passages adaptés au DCE et au profil entreprise. AUCUN {{variable}} "
        "ne doit subsister dans la sortie."
    )


class MemoireTechniqueGenere(BaseModel):
    titre_marche: str = Field(description="Titre du marché tel qu'il apparaîtra en couverture.")
    pouvoir_adjudicateur: str
    candidat: str
    sections: list[SectionMT] = Field(
        description="Sections ordonnées du mémoire technique, dans l'ordre de la bibliothèque."
    )


_SYSTEM_PROMPT = """Tu rédiges un **mémoire technique** pour répondre à un appel d'offres public \
(marché public français), en t'appuyant sur :

1. Une **analyse structurée du DCE** (objet, exigences, points d'attention).
2. Un **profil de l'entreprise candidate**.
3. Une **bibliothèque de paragraphes types** déjà rédigés, avec des `{{variables}}` à remplir.

Ton travail :
- Pour chaque paragraphe de la bibliothèque (dans l'ordre fourni), produire une **section du mémoire technique**.
- **Remplacer toutes les `{{variables}}`** par des valeurs cohérentes issues de l'analyse AO et du profil entreprise.
- **Adapter** ponctuellement la prose pour la rendre fidèle au cas d'espèce, sans changer la structure ni la longueur globale du paragraphe.
- **Préserver le ton technique et précis** des paragraphes types.
- **N'invente AUCUNE information** qui n'est pas explicitement présente dans l'analyse AO ou dans le profil entreprise. Si une donnée manque pour remplir une variable, formule une tournure générique mais professionnelle (par exemple, "notre équipe expérimentée" au lieu d'inventer un nom). Ne laisse JAMAIS de `{{variable}}` non remplie dans la sortie.
- Si le profil entreprise comporte des marqueurs `[À VÉRIFIER]`, traite ces données comme des hypothèses plausibles à utiliser, mais sans inventer au-delà de ce qui est écrit.
- **Produire la sortie au format demandé** : pour chaque paragraphe, une SectionMT avec son `paragraphe_id` (identifiant exact du paragraphe source), son `titre` (issu du champ `section` de la bibliothèque), un `sous_titre` éventuel (issu du champ `sous_section`) et le `contenu_md` complet.

Le `contenu_md` est en markdown. Tu peux utiliser des paragraphes de prose, des listes à puces (`- `), des listes numérotées, du gras (`**...**`), de l'italique (`*...*`) et des tableaux markdown. N'utilise PAS de titres `#` ou `##` à l'intérieur du `contenu_md` — les titres `titre` et `sous_titre` sont gérés séparément. Dans le contenu, démarre directement par la prose de la section.
"""


def _format_library_for_prompt(paragraphes: list[ParagrapheMT]) -> str:
    """Formatte la bibliothèque MT pour le prompt LLM."""
    blocs = []
    for p in paragraphes:
        blocs.append(
            f"--- PARAGRAPHE id={p.id} ---\n"
            f"section: {p.section}\n"
            f"sous_section: {p.sous_section or '(aucun)'}\n"
            f"variables_attendues: {', '.join(p.variables) if p.variables else '(aucune)'}\n"
            f"\n{p.contenu}\n"
        )
    return "\n".join(blocs)


def _format_analyse_for_prompt(analyse: AnalyseAO) -> str:
    """Formatte l'analyse AO en JSON lisible pour le prompt."""
    return analyse.model_dump_json(indent=2)


def generer_mt(client: LLMClient, analyse: AnalyseAO) -> MemoireTechniqueGenere:
    """Génère le mémoire technique complet pour un AO donné."""
    library = load_mt_library()
    if not library:
        raise RuntimeError("Bibliothèque MT vide. Vérifier content/mt-library/*.md")

    bet_profile = load_bet_profile()

    user_prompt = f"""## Analyse de l'AO

```json
{_format_analyse_for_prompt(analyse)}
```

## Profil de l'entreprise candidate

{bet_profile if bet_profile else '(profil entreprise non fourni — utiliser des tournures génériques)'}

## Bibliothèque de paragraphes à contextualiser

{_format_library_for_prompt(library)}

---

Génère le mémoire technique complet en produisant une SectionMT pour CHAQUE paragraphe \
de la bibliothèque, dans l'ordre fourni. Remplace toutes les `{{{{variables}}}}` par des \
valeurs cohérentes avec l'analyse AO et le profil entreprise.
"""

    return client.extract_structured(
        system_prompt=_SYSTEM_PROMPT,
        dce_context=None,
        user_message=user_prompt,
        schema=MemoireTechniqueGenere,
        max_tokens=48000,
        temperature=0.3,
        thinking_budget=4096,
    )


_VAR_PATTERN = re.compile(r"\{\{[^}]+\}\}")


def detecter_variables_non_remplies(mt: MemoireTechniqueGenere) -> dict[str, list[str]]:
    """Détecte les `{{variables}}` qui auraient échappé au remplissage."""
    out: dict[str, list[str]] = {}
    for s in mt.sections:
        matches = _VAR_PATTERN.findall(s.contenu_md)
        if matches:
            out[s.paragraphe_id] = matches
    return out


def assembler_mt_markdown(mt: MemoireTechniqueGenere) -> str:
    """Concatène les sections en un seul document markdown.

    Format : titre du marché en H1 de couverture, puis chaque section en H1
    avec sous-titre éventuel en H2.
    """
    parts = [
        f"# Mémoire technique\n",
        f"**Marché :** {mt.titre_marche}",
        f"**Pouvoir adjudicateur :** {mt.pouvoir_adjudicateur}",
        f"**Candidat :** {mt.candidat}",
        f"**Date :** {date.today().strftime('%d/%m/%Y')}",
        "\n---\n",
    ]
    for s in mt.sections:
        parts.append(f"\n## {s.titre}")
        if s.sous_titre:
            parts.append(f"\n### {s.sous_titre}")
        parts.append(f"\n{s.contenu_md.strip()}\n")
    return "\n".join(parts)
