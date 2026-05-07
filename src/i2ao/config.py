"""Configuration centrale : chemins projet, clé API, paramètres LLM."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env", override=True)

CONTENT_DIR = PROJECT_ROOT / "content"
PROFILES_DIR = CONTENT_DIR / "profiles"

# Profil actif par défaut (slug d'un dossier sous content/profiles/).
# Surclassable via la variable d'env PROFIL_ACTIF, et au runtime via la sidebar.
PROFIL_ACTIF_DEFAUT = os.environ.get("PROFIL_ACTIF", "pathologie-confortement")


def chemins_profil(slug: str) -> dict:
    """Renvoie les chemins (mt-library, dpgf-catalog, bet-profile) pour un profil donné."""
    base = PROFILES_DIR / slug
    return {
        "base": base,
        "mt_library": base / "mt-library",
        "dpgf_catalog": base / "dpgf-catalog",
        "bet_profile": base / "bet-profile.md",
    }


def lister_profils_disponibles() -> list[str]:
    """Renvoie la liste des slugs de profils valides (qui contiennent une mt-library)."""
    if not PROFILES_DIR.exists():
        return []
    return sorted(
        d.name
        for d in PROFILES_DIR.iterdir()
        if d.is_dir() and (d / "mt-library").exists()
    )


# Compatibilité rétroactive — pointe vers le profil actif par défaut au moment de l'import.
# Le code applicatif moderne devrait privilégier chemins_profil(slug).
_chemins = chemins_profil(PROFIL_ACTIF_DEFAUT)
MT_LIBRARY_DIR = _chemins["mt_library"]
DPGF_CATALOG_DIR = _chemins["dpgf_catalog"]
BET_PROFILE_PATH = _chemins["bet_profile"]

DATA_DIR = PROJECT_ROOT / "data"
SAMPLES_DIR = DATA_DIR / "samples"
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "output"
DB_PATH = DATA_DIR / "i2ao.db"

# Création défensive : sur Streamlit Cloud (et environnements à FS partiellement
# read-only) la création peut échouer pour certains dossiers. On ne fait pas
# planter l'import du module pour autant — les sites consommateurs créeront ce
# dont ils ont besoin à l'usage et géreront leurs propres erreurs.
for d in (DATA_DIR, SAMPLES_DIR, UPLOADS_DIR, OUTPUT_DIR):
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""
LLM_MODEL = "gemini-2.5-flash"
LLM_MAX_TOKENS = 8000

# Nom du candidat utilisé par défaut dans les livrables (lettre, MT, DPGF…).
# Surclassable via la variable d'environnement CANDIDAT_NOM dans .env.
CANDIDAT_NOM = os.environ.get("CANDIDAT_NOM", "BET candidat")
