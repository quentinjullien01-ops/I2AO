"""Moteur de génération de DPGF.

Pipeline :
  1. Le candidat dispose d'un catalogue de prestations chiffrées (content/dpgf-catalog/).
  2. Gemini lit le DCE + le catalogue et extrait le programme indicatif que le candidat
     doit chiffrer pour son DQE (typiquement décrit dans le CCTP, article "programme type").
  3. Pour chaque ligne du programme, on récupère le prix unitaire au catalogue et
     on calcule le montant.
  4. Sortie : un BPU complet (catalogue) + un DQE chiffré + total.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .content_loader import PrestationDPGF, load_dpgf_catalog
from .extractor import AnalyseAO
from .llm import LLMClient


class LigneProgrammeIndicatif(BaseModel):
    """Une ligne du programme indicatif extraite du DCE par Gemini."""

    code_prestation: str = Field(
        description="Code de la prestation au catalogue (ex : '1.02', '7.02', '8.01')."
    )
    quantite: float = Field(description="Quantité retenue pour le DQE.")
    justification: str = Field(
        description="Justification courte (≤ 30 mots) du choix du code et de la quantité, "
        "au regard du DCE."
    )


class ProgrammeDQE(BaseModel):
    """Programme indicatif que le candidat doit chiffrer pour son DQE."""

    description: str = Field(
        description="Synthèse en 1-2 phrases du programme indicatif tel qu'identifié dans le DCE."
    )
    lignes: list[LigneProgrammeIndicatif] = Field(
        description="Lignes du programme à chiffrer, avec code catalogue + quantité."
    )


class LigneChiffree(BaseModel):
    code: str
    libelle: str
    unite: str
    prix_unitaire: float
    quantite: float
    montant: float
    categorie: str
    justification: str | None = None


class DPGFGeneree(BaseModel):
    description_programme: str
    bpu: list[PrestationDPGF]
    dqe: list[LigneChiffree]
    montant_dqe_he: float
    lignes_orphelines: list[str] = Field(
        default_factory=list,
        description="Codes du programme qui n'ont pas trouvé de correspondance au catalogue.",
    )


_SYSTEM_PROMPT_PROGRAMME = """Tu es un expert en analyse de DCE de marchés publics français, \
spécialisé en bureau d'études structures pathologie/confortement.

Ton rôle : à partir d'un DCE et d'un **catalogue de prestations** d'un candidat (avec leurs \
codes, libellés et unités), identifier le **programme indicatif** que le candidat doit chiffrer \
pour son DQE (Détail Quantitatif Estimatif), et le traduire en lignes concrètes \
(code catalogue + quantité).

**Règles :**

1. Cherche dans le DCE — en priorité dans le CCTP — un article qui décrit un **programme indicatif**, \
**programme type** ou **DQE simulation** que le candidat doit valoriser à titre de simulation. \
Cet article peut être nommé "programme type", "DQE indicatif", "programme prévisionnel", etc.

2. Pour chaque type de prestation mentionnée dans ce programme, identifie LE code du catalogue \
le plus approprié. Si le programme dit "6 diagnostics structurels d'ampleur courante", choisis \
parmi les codes "1.02", "1.03" celui qui colle (ici "1.02" pour ouvrages courants R+4 à R+7).

3. **CRITIQUE — règle des unités :**
   - Pour les lignes dont l'unité est `forfait`, `mesure`, `sondage`, `unité`, `essai`, \
     `échantillon`, `mois`, `passage`, `jour`, `demi-journée`, `carotte` → la **quantité** est \
     un **nombre d'unités** (ex : 6 pour "6 diagnostics", 12 pour "12 mois de suivi").
   - Pour les lignes dont l'unité est `% travaux` (missions de MOE) → la **quantité** est \
     le **montant des travaux concernés en euros HT** (PAS un pourcentage, PAS un nombre de \
     missions). Le moteur appliquera lui-même le pourcentage. Exemple : pour "2 missions de MOE \
     sur opérations à 250 k€ HT travaux", il faut produire **DEUX lignes distinctes** sur le \
     code MOE pertinent (ex 7.02), avec quantité = 250000 chacune (PAS quantité = 2).

4. Si une catégorie du programme se décompose en plusieurs opérations de tailles différentes \
(typiquement les missions MOE), produis **une ligne par opération**, pas une ligne agrégée.

4bis. **CAS DES MARCHÉS AU FORFAIT (pas à bons de commande) :**
   - Quand le marché est ordinaire au forfait (cas typique : MAPA, mission MOE complète sur \
     un ouvrage unique), tu dois TOUJOURS inclure dans le programme :
     (a) le **chiffrage de la mission forfaitaire principale** (mission MOE de base ou complète) \
         avec le code MOE pertinent et la quantité = montant travaux concernés ;
     (b) les **éventuelles phases additionnelles** (EXE/VISA/OPC) si elles sont demandées au DCE ;
     (c) les **prestations complémentaires** (investigations supplémentaires, vacations) \
         si le DCE les distingue explicitement (typiquement un "BPU complémentaire").
   - Ne JAMAIS produire un programme qui omettrait la mission principale du forfait. \
     Le total DQE doit refléter la totalité du chiffrage à présenter par le candidat.

5. Si le DCE ne fournit pas explicitement de programme indicatif, propose un programme \
**plausible** pour ce type de marché (10 à 20 lignes), basé sur :
   - Le type de marché (à bons de commande / ordinaire),
   - Le montant maximum (et donc le volume prévisionnel d'activité),
   - La typologie de mission majoritaire (diag, MOE, expertise),
   - Les spécificités identifiées (RGA, pathologie, etc.).

6. Pour chaque ligne, fournis une **justification courte** (≤ 30 mots) qui référence le DCE \
ou la logique de proxy.

7. Ne retiens QUE des codes effectivement présents dans le catalogue fourni. Pas d'invention de codes.

Cible : un programme représentatif de l'activité prévisionnelle du marché, qui permettra \
au candidat de produire un DQE crédible.
"""


def _calculer_montant(prest: PrestationDPGF, quantite: float) -> float:
    """Multiplication adaptée à l'unité de la prestation.

    Pour `% travaux` : prix_unitaire est un pourcentage (ex 11.0 pour 11%) et la
    quantite est le **montant des travaux** ; on applique donc le pourcentage.
    Pour les autres unités : multiplication directe.
    """
    if prest.unite.strip().lower() in {"% travaux", "%travaux", "%"}:
        return round(prest.prix_unitaire / 100.0 * quantite, 2)
    return round(prest.prix_unitaire * quantite, 2)


def _format_catalog_for_prompt(catalog: list[PrestationDPGF]) -> str:
    blocs = []
    by_cat: dict[str, list[PrestationDPGF]] = {}
    for p in catalog:
        by_cat.setdefault(p.categorie, []).append(p)
    for cat, prestations in by_cat.items():
        blocs.append(f"### {cat}")
        for p in prestations:
            blocs.append(f"  {p.code}  | {p.libelle}  | unité : {p.unite}")
    return "\n".join(blocs)


def extraire_programme_dqe(
    client: LLMClient, analyse: AnalyseAO, dce_concatene: str
) -> ProgrammeDQE:
    """Demande à Gemini d'extraire le programme indicatif pour DQE."""
    catalog = load_dpgf_catalog()
    if not catalog:
        raise RuntimeError("Catalogue DPGF vide. Vérifier content/dpgf-catalog/*.yaml")

    user_prompt = f"""## Catalogue de prestations du candidat

{_format_catalog_for_prompt(catalog)}

## Analyse de l'AO

```json
{analyse.model_dump_json(indent=2)}
```

## DCE complet (texte extrait)

{dce_concatene}

---

Identifie le programme indicatif que le candidat doit chiffrer pour son DQE et \
traduis-le en lignes (code catalogue + quantité + justification courte).
"""

    return client.extract_structured(
        system_prompt=_SYSTEM_PROMPT_PROGRAMME,
        dce_context=None,
        user_message=user_prompt,
        schema=ProgrammeDQE,
        max_tokens=8000,
        temperature=0.2,
        thinking_budget=2048,
    )


def generer_dpgf(
    client: LLMClient, analyse: AnalyseAO, dce_concatene: str
) -> DPGFGeneree:
    """Génère la DPGF complète : BPU au catalogue + DQE chiffré du programme indicatif."""
    catalog = load_dpgf_catalog()
    catalog_by_code: dict[str, PrestationDPGF] = {p.code: p for p in catalog}

    programme = extraire_programme_dqe(client, analyse, dce_concatene)

    dqe: list[LigneChiffree] = []
    orphelines: list[str] = []
    montant_total = 0.0

    for ligne in programme.lignes:
        prest = catalog_by_code.get(ligne.code_prestation)
        if not prest:
            orphelines.append(ligne.code_prestation)
            continue
        montant = _calculer_montant(prest, ligne.quantite)
        montant_total += montant
        dqe.append(
            LigneChiffree(
                code=prest.code,
                libelle=prest.libelle,
                unite=prest.unite,
                prix_unitaire=prest.prix_unitaire,
                quantite=ligne.quantite,
                montant=montant,
                categorie=prest.categorie,
                justification=ligne.justification,
            )
        )

    return DPGFGeneree(
        description_programme=programme.description,
        bpu=catalog,
        dqe=dqe,
        montant_dqe_he=round(montant_total, 2),
        lignes_orphelines=orphelines,
    )
