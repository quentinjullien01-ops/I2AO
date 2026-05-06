"""Configuration centrale : chemins projet, clé API, paramètres LLM."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env", override=True)

CONTENT_DIR = PROJECT_ROOT / "content"
MT_LIBRARY_DIR = CONTENT_DIR / "mt-library"
DPGF_CATALOG_DIR = CONTENT_DIR / "dpgf-catalog"
BET_PROFILE_PATH = CONTENT_DIR / "bet-profile.md"

DATA_DIR = PROJECT_ROOT / "data"
SAMPLES_DIR = DATA_DIR / "samples"
UPLOADS_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "output"
DB_PATH = DATA_DIR / "i2ao.db"

for d in (DATA_DIR, SAMPLES_DIR, UPLOADS_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""
LLM_MODEL = "gemini-2.5-flash"
LLM_MAX_TOKENS = 8000

# Nom du candidat utilisé par défaut dans les livrables (lettre, MT, DPGF…).
# Surclassable via la variable d'environnement CANDIDAT_NOM dans .env.
CANDIDAT_NOM = os.environ.get("CANDIDAT_NOM", "BET candidat")
