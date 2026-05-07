"""Administration des profils métier : création, import / export ZIP, listing.

Sur Streamlit Cloud le filesystem est éphémère : les profils créés ou importés
en runtime sont perdus au prochain redéploiement. Toute création produit donc
aussi un ZIP téléchargeable que l'utilisateur peut conserver et committer dans
sa fork pour persistence durable.
"""

from __future__ import annotations

import io
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .config import PROFILES_DIR

# ---------------------------------------------------------------------------
# Templates pour la création de profil neuf
# ---------------------------------------------------------------------------

_TEMPLATE_BET_PROFILE = """---
status: template
specialite: {specialite}
note: |
  Profil créé via le wizard I2AO le {date_creation}. À compléter avec les
  données réelles du BET avant utilisation en production.
---

# Profil de l'entreprise candidate — {specialite}

## Identité

- **Raison sociale :** [À RENSEIGNER]
- **Forme juridique :** [À RENSEIGNER]
- **Année de création :** [À RENSEIGNER]
- **Localisation :** [À RENSEIGNER]
- **Effectif structures :** [À RENSEIGNER]

## Positionnement

[À RENSEIGNER — décrire en 2-3 phrases le cœur de métier et ce qui distingue
l'entreprise des autres BET du même créneau.]

## Domaines d'intervention

- **Matériaux / typologies :** [À RENSEIGNER]
- **Compétences techniques principales :** [À RENSEIGNER]

## Moyens techniques

- **Logiciels de calcul :** [À RENSEIGNER]
- **Outils numériques :** [À RENSEIGNER — BIM, plateforme collaborative, etc.]

## Qualifications professionnelles

[À RENSEIGNER — qualifications OPQIBI, certifications, accréditations]

## Démarche qualité

[À RENSEIGNER — procédures de relecture, plan qualité, certifications ISO]

## Atouts génériques

1. [À RENSEIGNER — atout 1]
2. [À RENSEIGNER — atout 2]
3. [À RENSEIGNER — atout 3]
"""


_TEMPLATE_PARAGRAPHE_INTRO = """---
id: mt-{slug}-00-presentation
section: Présentation du candidat
sous_section: null
ordre: 1
tags:
  - presentation
adapte_a:
  - tous
variables:
  - nom_candidat
duree_estimee_lecture: "1 min"
---

## Présentation du candidat

**{{{{nom_candidat}}}}** est un bureau d'études techniques spécialisé en {specialite}.

[À RÉDIGER : présentation synthétique du candidat, son cœur de métier, son équipe,
ses moyens. 3 à 5 phrases factuelles, sans marketing creux.]
"""


_TEMPLATE_DPGF = """# Catalogue de prestations — {specialite}
# Renseigner les prestations avec leurs prix unitaires HT.
# Unités possibles : forfait, jour, demi-journée, mesure, sondage, % travaux, ...

prestations:
  - code: "1.01"
    libelle: "[À RENSEIGNER]"
    unite: "forfait"
    prix_unitaire: 0
    categorie: "Études"
    tags: []
    note: "Premier exemple de prestation — à remplacer."
"""


# ---------------------------------------------------------------------------
# Listing avec stats
# ---------------------------------------------------------------------------


@dataclass
class StatProfil:
    slug: str
    nb_paragraphes: int
    nb_prestations: int
    profil_template: bool  # True si le bet-profile.md contient encore [À RENSEIGNER]
    taille_octets: int


def lister_profils_avec_stats() -> list[StatProfil]:
    """Liste tous les profils valides avec quelques statistiques."""
    from .content_loader import load_bet_profile, load_dpgf_catalog, load_mt_library

    if not PROFILES_DIR.exists():
        return []

    out: list[StatProfil] = []
    for d in sorted(PROFILES_DIR.iterdir()):
        if not d.is_dir() or not (d / "mt-library").exists():
            continue
        bet = load_bet_profile(d.name)
        taille = sum(p.stat().st_size for p in d.rglob("*") if p.is_file())
        out.append(
            StatProfil(
                slug=d.name,
                nb_paragraphes=len(load_mt_library(d.name)),
                nb_prestations=len(load_dpgf_catalog(d.name)),
                profil_template="[À RENSEIGNER]" in bet,
                taille_octets=taille,
            )
        )
    return out


# ---------------------------------------------------------------------------
# Création
# ---------------------------------------------------------------------------


_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")


def slug_valide(slug: str) -> bool:
    """Slug = minuscules + chiffres + tirets, commence par une lettre, ≥ 2 caractères."""
    if not slug or len(slug) < 2 or len(slug) > 50:
        return False
    return bool(_SLUG_RE.match(slug))


def creer_profil(
    slug: str,
    specialite: str,
    *,
    copier_depuis: str | None = None,
) -> Path:
    """Crée un nouveau dossier de profil sous content/profiles/<slug>/.

    Si `copier_depuis` est un slug existant, le profil source est dupliqué.
    Sinon, des templates vierges sont générés.

    Retourne le Path du dossier créé.
    """
    from datetime import date

    if not slug_valide(slug):
        raise ValueError(
            f"Slug invalide : '{slug}'. Doit commencer par une lettre, contenir "
            "uniquement minuscules / chiffres / tirets, et faire 2 à 50 caractères."
        )

    target = PROFILES_DIR / slug
    if target.exists():
        raise ValueError(f"Le profil '{slug}' existe déjà sous {target.relative_to(PROFILES_DIR.parent)}.")

    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    if copier_depuis:
        source = PROFILES_DIR / copier_depuis
        if not source.exists() or not source.is_dir():
            raise ValueError(f"Profil source '{copier_depuis}' introuvable.")
        shutil.copytree(source, target)
        return target

    # Génération de templates vierges
    target.mkdir()
    (target / "mt-library").mkdir()
    (target / "dpgf-catalog").mkdir()

    (target / "bet-profile.md").write_text(
        _TEMPLATE_BET_PROFILE.format(
            specialite=specialite,
            date_creation=date.today().isoformat(),
        ),
        encoding="utf-8",
    )
    (target / "mt-library" / "01-presentation-candidat.md").write_text(
        _TEMPLATE_PARAGRAPHE_INTRO.format(slug=slug, specialite=specialite),
        encoding="utf-8",
    )
    (target / "dpgf-catalog" / "prestations.yaml").write_text(
        _TEMPLATE_DPGF.format(specialite=specialite),
        encoding="utf-8",
    )

    return target


# ---------------------------------------------------------------------------
# Suppression
# ---------------------------------------------------------------------------


def supprimer_profil(slug: str) -> None:
    target = PROFILES_DIR / slug
    if not target.exists():
        raise ValueError(f"Profil '{slug}' introuvable.")
    shutil.rmtree(target)


# ---------------------------------------------------------------------------
# Export ZIP
# ---------------------------------------------------------------------------


def exporter_profil_zip(slug: str) -> bytes:
    """Renvoie un ZIP du profil entier (à servir via st.download_button)."""
    source = PROFILES_DIR / slug
    if not source.exists() or not source.is_dir():
        raise ValueError(f"Profil '{slug}' introuvable.")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in source.rglob("*"):
            if path.is_file():
                # Conserve la racine <slug>/ dans le ZIP pour faciliter
                # l'import et le commit dans content/profiles/.
                arcname = Path(slug) / path.relative_to(source)
                zf.write(path, arcname=str(arcname))
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Import ZIP
# ---------------------------------------------------------------------------


def importer_profil_zip(zip_bytes: bytes, *, slug_cible: str | None = None) -> str:
    """Importe un profil ZIP. Renvoie le slug effectivement utilisé.

    Le ZIP doit contenir un seul dossier racine <slug>/ avec mt-library/,
    dpgf-catalog/ et bet-profile.md (équivalent du format produit par
    `exporter_profil_zip`).

    Si `slug_cible` est fourni, le dossier racine du ZIP est renommé.
    """
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = [n for n in zf.namelist() if n and not n.endswith("/")]
        if not names:
            raise ValueError("ZIP vide.")

        # Détecte le slug racine
        racines = {Path(n).parts[0] for n in names if Path(n).parts}
        if len(racines) != 1:
            raise ValueError(
                f"Le ZIP doit contenir un seul dossier racine. Trouvés : {sorted(racines)}."
            )
        slug_source = racines.pop()
        slug = slug_cible or slug_source

        if not slug_valide(slug):
            raise ValueError(f"Slug '{slug}' invalide (cf. règles de nommage).")

        target = PROFILES_DIR / slug
        if target.exists():
            raise ValueError(
                f"Le profil '{slug}' existe déjà — supprime-le d'abord ou choisis un autre slug cible."
            )

        # Validation de structure : doit contenir au moins bet-profile.md et mt-library/
        a_bet_profile = any(n.endswith("bet-profile.md") for n in names)
        a_mt_library = any("/mt-library/" in n or n.endswith("/mt-library/") for n in names)
        if not (a_bet_profile and a_mt_library):
            raise ValueError(
                "Structure de ZIP invalide : il doit contenir bet-profile.md et un dossier mt-library/."
            )

        target.mkdir()
        for name in names:
            parts = Path(name).parts
            if len(parts) < 2:
                continue  # juste le dossier racine, on ignore
            relative = Path(*parts[1:])
            full_path = target / relative
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with full_path.open("wb") as f:
                f.write(zf.read(name))

        return slug
