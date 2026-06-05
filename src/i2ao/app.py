"""Application Streamlit I2AO.

Lancement :
    .venv/Scripts/streamlit.exe run src/i2ao/app.py

Couvre tout le pipeline : upload DCE -> analyse -> mémoire technique -> DPGF,
avec téléchargement des livrables (DOCX, XLSX, JSON).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

# Permet le `import i2ao.*` quand streamlit run est appele depuis la racine projet
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

# === Purge defensive du cache de modules i2ao.* avant chaque rerun ===
#
# Streamlit (notamment sur Streamlit Cloud) ré-exécute ce script à chaque
# interaction utilisateur sans relancer le process Python. Conséquence :
# `sys.modules` conserve les références aux anciennes versions des modules
# i2ao.*, ce qui provoque des `ImportError` ou `KeyError` parasites quand le
# code change (renommage de fonctions, ajout de nouveaux modules, refactor).
#
# Nettoyer ces entrées avant les imports force Python à recharger les fichiers
# .py depuis le disque à chaque run. Coût : quelques millisecondes au rerun.
# Bénéfice : zéro KeyError/ImportError de cache après une mise à jour.
for _mod_name in list(sys.modules.keys()):
    if _mod_name == "i2ao" or _mod_name.startswith("i2ao."):
        del sys.modules[_mod_name]

LOGO_PATH = PROJECT_ROOT / "assets" / "logo.svg"

import streamlit as st

from i2ao.affaires import (
    Affaire,
    ajouter_piece,
    creer_affaire,
    get_affaire,
    initialiser_demo_si_absente,
    lister_affaires,
    supprimer_affaire,
)
from i2ao.candidature import (
    LettrePresentation,
    creer_pack_zip,
    exporter_lettre_docx,
    generer_lettre,
)
from i2ao.charts import (
    bar_comparatif,
    bar_dqe_par_categorie,
    bar_exigences_par_categorie,
    bar_exigences_par_importance,
    donut_couverture,
    donut_repartition_dqe,
    gauge_score,
    scatter3d_exigences,
    surface3d_dqe,
)
from i2ao.config import (
    CANDIDAT_NOM,
    GOOGLE_API_KEY,
    LLM_MODEL,
    PROFIL_ACTIF_DEFAUT,
    lister_profils_disponibles,
)
from i2ao.coverage import RapportCouverture, evaluer_couverture
from i2ao.docx_export import exporter_mt_docx
from i2ao.dpgf_engine import DPGFGeneree, generer_dpgf
from i2ao.extractor import AnalyseAO, concatener_dce, extraire_analyse_ao
from i2ao.llm import LLMClient, LLMError, LLMOverloadError
from i2ao.mt_engine import (
    MemoireTechniqueGenere,
    detecter_variables_non_remplies,
    generer_mt,
)
from i2ao.pdf_parser import detect_type_piece, parse_pdf
from i2ao.profiles_admin import (
    creer_profil,
    exporter_profil_zip,
    importer_profil_zip,
    lister_profils_avec_stats,
    slug_valide,
    supprimer_profil,
)
from i2ao.synthese import SyntheseDirection, exporter_synthese_docx, generer_synthese
from i2ao.usage_tracker import get_session_usage, reset_session_usage
from i2ao.xlsx_export import exporter_dpgf_xlsx


# ---------------------------------------------------------------------------
# Configuration de la page
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="I2AO — Outil AO BET pathologie/structures",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def _load_logo_svg() -> str:
    if LOGO_PATH.exists():
        return LOGO_PATH.read_text(encoding="utf-8")
    return ""


@st.cache_data
def _logo_data_url() -> str:
    """Renvoie le logo encodé en data-URL base64 pour usage dans <img src=...>.

    Streamlit sanitize les SVG inline ; passer par une img/data-url contourne le filtre.
    """
    import base64

    svg = _load_logo_svg()
    if not svg:
        return ""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


# ---------------------------------------------------------------------------
# Style custom — "Mission Control" dark theme avec effets 3D et animations
# ---------------------------------------------------------------------------

_CUSTOM_CSS = """
<style>
/* ============================================================
   I2AO — Design System 2.0  |  "Mission Control"
   ============================================================ */

:root {
    --c-bg:           #030d1f;
    --c-bg2:          #071428;
    --c-glass:        rgba(255,255,255,0.04);
    --c-glass-border: rgba(255,255,255,0.09);
    --c-primary:      #38bdf8;
    --c-primary-glow: rgba(56,189,248,0.35);
    --c-indigo:       #818cf8;
    --c-success:      #10b981;
    --c-warning:      #f59e0b;
    --c-danger:       #ef4444;
    --c-text:         rgba(255,255,255,0.90);
    --c-muted:        rgba(255,255,255,0.40);
}

/* === FOND GÉNÉRAL ============================================= */
[data-testid="stAppViewContainer"] {
    background: var(--c-bg) !important;
}

/* Orbes lumineux animés en arrière-plan */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 900px 700px at 10% 35%,  rgba(56,189,248,0.07)  0%, transparent 65%),
        radial-gradient(ellipse 700px 900px at 88% 15%,  rgba(129,140,248,0.06) 0%, transparent 65%),
        radial-gradient(ellipse 800px 500px at 55% 95%,  rgba(16,185,129,0.04)  0%, transparent 65%);
    animation: bgPulse 14s ease-in-out infinite alternate;
    pointer-events: none;
    z-index: 0;
}
@keyframes bgPulse {
    0%   { opacity:.6; transform: scale(1)    translate(0,0); }
    50%  { opacity:1;  transform: scale(1.06) translate(1%,-1%); }
    100% { opacity:.7; transform: scale(.97)  translate(-1%,1%); }
}

/* Grille fine en arrière-plan */
[data-testid="stAppViewContainer"]::after {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(56,189,248,.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(56,189,248,.025) 1px, transparent 1px);
    background-size: 64px 64px;
    pointer-events: none;
    z-index: 0;
}

/* === SIDEBAR ================================================== */
section[data-testid="stSidebar"] {
    background: rgba(3,13,31,.96) !important;
    border-right: 1px solid rgba(56,189,248,.14) !important;
    backdrop-filter: blur(20px);
}
section[data-testid="stSidebar"]::before {
    content: '';
    position: absolute; inset: 0;
    background: linear-gradient(180deg, rgba(56,189,248,.06) 0%, transparent 35%);
    pointer-events: none;
}
section[data-testid="stSidebar"] * { color: var(--c-text) !important; }
section[data-testid="stSidebar"] h1 {
    background: linear-gradient(135deg, #e0f2fe, var(--c-primary));
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    font-family: 'Times New Roman', Georgia, serif;
    font-weight: 800 !important;
}

/* === CONTENU PRINCIPAL ======================================= */
.block-container { padding-top: 2rem !important; }
.main p, .main li, .main td { color: var(--c-text); }
.main strong { color: #fff; }

/* Titres avec gradient animé */
.main h1 {
    background: linear-gradient(120deg, #e0f2fe 0%, var(--c-primary) 45%, var(--c-indigo) 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-family: 'Times New Roman', Georgia, serif;
    font-weight: 800;
    letter-spacing: -.5px;
    animation: gradShift 6s linear infinite alternate;
}
@keyframes gradShift {
    from { background-position: 0% center; }
    to   { background-position: 100% center; }
}

.main h2 {
    color: var(--c-primary);
    font-weight: 600;
    position: relative;
    padding-bottom: 6px;
}
.main h2::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0;
    height: 2px; width: 0;
    background: linear-gradient(90deg, var(--c-primary), transparent);
    border-radius: 2px;
    animation: lineGrow .55s ease forwards;
}
@keyframes lineGrow {
    to { width: 48px; }
}

.main h3, .main h4, .main h5 {
    color: rgba(255,255,255,.85);
}

/* === CARTES MÉTRIQUES — glassmorphism + 3D tilt ============= */
[data-testid="stMetric"] {
    background: var(--c-glass) !important;
    border: 1px solid var(--c-glass-border) !important;
    border-radius: 18px !important;
    padding: 1.3rem 1.5rem !important;
    backdrop-filter: blur(14px) !important;
    transition: transform .25s ease, box-shadow .25s ease !important;
    transform-style: preserve-3d;
    position: relative;
    overflow: hidden;
    cursor: default;
}
[data-testid="stMetric"]::before {
    content: '';
    position: absolute; top:-60%; left:-60%;
    width: 220%; height: 220%;
    background: radial-gradient(circle at 50% 50%, rgba(56,189,248,.07), transparent 55%);
    opacity: 0;
    transition: opacity .3s;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-7px) rotateX(5deg) scale(1.03) !important;
    box-shadow:
        0 22px 55px rgba(56,189,248,.22),
        0 0 0 1px rgba(56,189,248,.22) !important;
}
[data-testid="stMetric"]:hover::before { opacity: 1; }

[data-testid="stMetricValue"] {
    color: var(--c-primary) !important;
    font-weight: 800 !important;
    font-size: 2rem !important;
    text-shadow: 0 0 22px var(--c-primary-glow);
}
[data-testid="stMetricLabel"] {
    color: var(--c-muted) !important;
    font-size: .74rem !important;
    text-transform: uppercase;
    letter-spacing: 1.4px;
}

/* === ONGLETS ================================================= */
[data-testid="stTabs"] {
    border-bottom: 1px solid rgba(56,189,248,.12) !important;
}
[data-testid="stTabs"] button[role="tab"] {
    color: var(--c-muted) !important;
    font-weight: 500;
    border-radius: 10px 10px 0 0 !important;
    transition: all .2s ease !important;
    position: relative;
}
[data-testid="stTabs"] button[role="tab"]:hover {
    color: var(--c-primary) !important;
    background: rgba(56,189,248,.07) !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: var(--c-primary) !important;
    font-weight: 700;
    background: rgba(56,189,248,.09) !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"]::after {
    content: '';
    position: absolute;
    bottom: 0; left: 10%; right: 10%;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--c-primary), transparent);
    border-radius: 2px;
    box-shadow: 0 0 10px var(--c-primary-glow);
}

/* Fade-in sur chaque rendu de panneau d'onglet */
[data-testid="stTabPanel"] {
    animation: fadeUp .38s ease;
}
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* === BOUTONS ================================================= */
.stButton button {
    border-radius: 11px !important;
    font-weight: 600 !important;
    transition: all .22s ease !important;
    position: relative;
    overflow: hidden;
}
.stButton button[kind="primary"] {
    background: linear-gradient(135deg, #0ea5e9 0%, #1a3d6e 100%) !important;
    border: none !important;
    color: #fff !important;
    box-shadow: 0 4px 22px rgba(14,165,233,.32) !important;
}
.stButton button[kind="primary"]:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 10px 32px rgba(14,165,233,.5) !important;
}
/* Shimmer continu sur les boutons primaires */
.stButton button[kind="primary"]::after {
    content: '';
    position: absolute;
    top: -50%; left: -70%;
    width: 35%; height: 200%;
    background: rgba(255,255,255,.18);
    transform: skewX(-22deg);
    animation: shimmer 3.5s ease infinite;
}
@keyframes shimmer {
    0%   { left: -70%; }
    100% { left: 170%; }
}

/* Boutons de téléchargement */
.stDownloadButton button {
    background: rgba(16,185,129,.1) !important;
    border: 1px solid rgba(16,185,129,.35) !important;
    color: var(--c-success) !important;
    border-radius: 11px !important;
    transition: all .2s ease !important;
}
.stDownloadButton button:hover {
    background: rgba(16,185,129,.2) !important;
    box-shadow: 0 6px 22px rgba(16,185,129,.3) !important;
    transform: translateY(-2px) !important;
}

/* === LIGNE DE STATUT ========================================= */
.i2ao-status-line {
    background: rgba(56,189,248,.05);
    border: 1px solid rgba(56,189,248,.18);
    border-left: 3px solid var(--c-primary);
    border-radius: 12px;
    padding: 12px 18px;
    font-size: .88rem;
    color: var(--c-text);
    margin-bottom: 1.3rem;
    box-shadow: 0 0 24px rgba(56,189,248,.06);
    animation: fadeUp .4s ease;
}
.i2ao-status-line .ok {
    color: var(--c-success);
    font-weight: 700;
    text-shadow: 0 0 10px rgba(16,185,129,.45);
}
.i2ao-status-line .ko { opacity: .28; }

/* === HERO LANDING ============================================ */
.i2ao-hero {
    background: linear-gradient(135deg, #020d1e 0%, #071428 45%, #0d2247 100%);
    border: 1px solid rgba(56,189,248,.18);
    border-radius: 22px;
    padding: 3.5rem 3rem;
    margin: .5rem 0 2rem;
    position: relative;
    overflow: hidden;
    box-shadow:
        0 28px 80px rgba(56,189,248,.10),
        inset 0 1px 0 rgba(255,255,255,.06);
}
/* Orbe droit */
.i2ao-hero::before {
    content: '';
    position: absolute; top:-120px; right:-120px;
    width: 450px; height: 450px;
    background: radial-gradient(circle, rgba(56,189,248,.13) 0%, transparent 65%);
    animation: heroOrb 7s ease-in-out infinite alternate;
}
/* Orbe gauche */
.i2ao-hero::after {
    content: '';
    position: absolute; bottom:-100px; left:-100px;
    width: 350px; height: 350px;
    background: radial-gradient(circle, rgba(129,140,248,.09) 0%, transparent 65%);
    animation: heroOrb2 9s ease-in-out infinite alternate;
}
@keyframes heroOrb  { to { transform: translate(-35px,35px) scale(1.22); } }
@keyframes heroOrb2 { to { transform: translate(25px,-25px) scale(1.18); } }

.i2ao-hero h1 {
    color: #fff !important;
    -webkit-text-fill-color: #fff !important;
    font-size: 2.9rem;
    font-weight: 800;
    margin: 0 0 .6rem;
    text-shadow: 0 0 40px rgba(56,189,248,.4);
    position: relative; z-index: 1;
}
.i2ao-hero p {
    color: rgba(255,255,255,.75);
    font-size: 1.12rem;
    position: relative; z-index: 1;
}

/* === EXPANDERS =============================================== */
[data-testid="stExpander"] {
    background: var(--c-glass) !important;
    border: 1px solid var(--c-glass-border) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(10px);
    transition: border-color .2s;
}
[data-testid="stExpander"]:hover {
    border-color: rgba(56,189,248,.26) !important;
}
[data-testid="stExpander"] summary {
    color: var(--c-text) !important;
}

/* === DATAFRAMES ============================================== */
[data-testid="stDataFrame"] {
    border-radius: 14px !important;
    overflow: hidden;
    border: 1px solid var(--c-glass-border) !important;
}

/* === ALERTES ================================================= */
[data-testid="stAlert"] {
    border-radius: 14px !important;
    border-left-width: 3px !important;
    backdrop-filter: blur(8px);
}

/* === CONTAINERS À BORD ====================================== */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--c-glass) !important;
    border: 1px solid var(--c-glass-border) !important;
    border-radius: 18px !important;
    backdrop-filter: blur(10px);
}

/* === DIVIDERS =============================================== */
hr {
    border: none !important;
    border-top: 1px solid rgba(56,189,248,.10) !important;
    margin: 1.8rem 0 !important;
}

/* === CAPTIONS =============================================== */
.stCaption, [data-testid="stCaptionContainer"] {
    color: var(--c-muted) !important;
    font-style: italic;
}

/* Scrollbar fine et discrète */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(56,189,248,.25);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(56,189,248,.45);
}
</style>
"""

# Particules CSS pure — Streamlit bloque les <script>, on utilise des @keyframes
# 30 points avec positions/durées/délais variés, entièrement CSS, aucun JS requis.
_PARTICLES_CSS = """
<style>
.i2ao-particles {
    position: fixed; inset: 0;
    overflow: hidden; pointer-events: none; z-index: 1;
}
.i2ao-particles span {
    position: absolute;
    border-radius: 50%;
    background: rgba(56,189,248,.65);
    box-shadow: 0 0 6px rgba(56,189,248,.4);
    animation: floatDot linear infinite;
}
@keyframes floatDot {
    0%   { transform: translateY(100vh) scale(0); opacity: 0; }
    10%  { opacity: 1; }
    90%  { opacity: .6; }
    100% { transform: translateY(-10vh) scale(1); opacity: 0; }
}
/* 30 particules avec positions, tailles et timings uniques */
.i2ao-particles span:nth-child(1)  {left:3%;  width:3px; height:3px; animation-duration:18s; animation-delay:0s;}
.i2ao-particles span:nth-child(2)  {left:8%;  width:2px; height:2px; animation-duration:22s; animation-delay:-4s;}
.i2ao-particles span:nth-child(3)  {left:14%; width:4px; height:4px; animation-duration:16s; animation-delay:-8s;}
.i2ao-particles span:nth-child(4)  {left:20%; width:2px; height:2px; animation-duration:25s; animation-delay:-2s;}
.i2ao-particles span:nth-child(5)  {left:27%; width:3px; height:3px; animation-duration:19s; animation-delay:-12s;}
.i2ao-particles span:nth-child(6)  {left:33%; width:2px; height:2px; animation-duration:21s; animation-delay:-6s;}
.i2ao-particles span:nth-child(7)  {left:39%; width:4px; height:4px; animation-duration:17s; animation-delay:-3s;}
.i2ao-particles span:nth-child(8)  {left:45%; width:2px; height:2px; animation-duration:23s; animation-delay:-9s;}
.i2ao-particles span:nth-child(9)  {left:52%; width:3px; height:3px; animation-duration:20s; animation-delay:-1s;}
.i2ao-particles span:nth-child(10) {left:58%; width:2px; height:2px; animation-duration:24s; animation-delay:-7s;}
.i2ao-particles span:nth-child(11) {left:64%; width:4px; height:4px; animation-duration:15s; animation-delay:-11s;}
.i2ao-particles span:nth-child(12) {left:70%; width:2px; height:2px; animation-duration:26s; animation-delay:-5s;}
.i2ao-particles span:nth-child(13) {left:76%; width:3px; height:3px; animation-duration:18s; animation-delay:-13s;}
.i2ao-particles span:nth-child(14) {left:82%; width:2px; height:2px; animation-duration:22s; animation-delay:-2s;}
.i2ao-particles span:nth-child(15) {left:88%; width:4px; height:4px; animation-duration:19s; animation-delay:-8s;}
.i2ao-particles span:nth-child(16) {left:94%; width:2px; height:2px; animation-duration:21s; animation-delay:-4s;}
.i2ao-particles span:nth-child(17) {left:6%;  width:3px; height:3px; animation-duration:28s; animation-delay:-16s;}
.i2ao-particles span:nth-child(18) {left:12%; width:2px; height:2px; animation-duration:20s; animation-delay:-10s;}
.i2ao-particles span:nth-child(19) {left:24%; width:3px; height:3px; animation-duration:23s; animation-delay:-14s;}
.i2ao-particles span:nth-child(20) {left:36%; width:2px; height:2px; animation-duration:17s; animation-delay:-6s;}
.i2ao-particles span:nth-child(21) {left:48%; width:4px; height:4px; animation-duration:25s; animation-delay:-3s;}
.i2ao-particles span:nth-child(22) {left:55%; width:2px; height:2px; animation-duration:18s; animation-delay:-17s;}
.i2ao-particles span:nth-child(23) {left:62%; width:3px; height:3px; animation-duration:22s; animation-delay:-9s;}
.i2ao-particles span:nth-child(24) {left:73%; width:2px; height:2px; animation-duration:16s; animation-delay:-5s;}
.i2ao-particles span:nth-child(25) {left:79%; width:3px; height:3px; animation-duration:24s; animation-delay:-12s;}
.i2ao-particles span:nth-child(26) {left:85%; width:2px; height:2px; animation-duration:20s; animation-delay:-1s;}
.i2ao-particles span:nth-child(27) {left:91%; width:4px; height:4px; animation-duration:19s; animation-delay:-7s;}
.i2ao-particles span:nth-child(28) {left:16%; width:2px; height:2px; animation-duration:27s; animation-delay:-15s;}
.i2ao-particles span:nth-child(29) {left:43%; width:3px; height:3px; animation-duration:21s; animation-delay:-11s;}
.i2ao-particles span:nth-child(30) {left:67%; width:2px; height:2px; animation-duration:23s; animation-delay:-4s;}
</style>
<div class="i2ao-particles">
<span></span><span></span><span></span><span></span><span></span>
<span></span><span></span><span></span><span></span><span></span>
<span></span><span></span><span></span><span></span><span></span>
<span></span><span></span><span></span><span></span><span></span>
<span></span><span></span><span></span><span></span><span></span>
<span></span><span></span><span></span><span></span><span></span>
</div>
"""

st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)
st.markdown(_PARTICLES_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@st.cache_resource
def get_llm_client() -> LLMClient | None:
    if not GOOGLE_API_KEY:
        return None
    try:
        return LLMClient()
    except LLMError:
        return None


def is_mode_presentation() -> bool:
    """Renvoie True si l'utilisateur a activé le mode pitch épuré."""
    return bool(st.session_state.get("mode_presentation", False))


def get_profil_actif() -> str:
    """Renvoie le slug du profil actuellement sélectionné (sidebar ou défaut)."""
    return st.session_state.get("profil_actif", PROFIL_ACTIF_DEFAUT)


def afficher_erreur_llm(exc: Exception, etape: str) -> None:
    """Affiche un message convivial pour les erreurs LLM (5xx, quota, etc.)."""
    if isinstance(exc, LLMOverloadError):
        st.error(
            f"⏳ Gemini est temporairement saturé pendant l'étape « {etape} ». "
            "Plusieurs retries automatiques ont échoué. **Réessaye dans 1 à 5 minutes** "
            "en cliquant sur le bouton « Regénérer » — c'est généralement transitoire."
        )
    else:
        st.error(
            f"❌ Erreur LLM pendant l'étape « {etape} » : {exc}. "
            "Vérifie ta clé API Gemini (sidebar) et le quota de ton projet Google AI Studio."
        )


def piece_humaine(code: str) -> str:
    return {
        "RC": "📋 Règlement de Consultation",
        "CCAP": "📜 CCAP",
        "CCTP": "🔧 CCTP",
        "BPU": "💶 BPU",
        "DPGF": "💰 DPGF",
        "AE": "📝 Acte d'engagement",
        "autre": "📎 Autre",
    }.get(code, f"📎 {code}")


def charger_pieces(affaire: Affaire) -> list[tuple[str, str, str, int, list[str]]]:
    """Renvoie la liste des pieces avec texte extrait + avertissements éventuels.

    Tuple : (nom_fichier, type, texte, nb_pages, avertissements)
    """
    out = []
    for pdf in sorted(affaire.pieces_dir.glob("*.pdf")):
        r = parse_pdf(pdf)
        type_p = detect_type_piece(pdf.name, r.texte_normalise)
        out.append((pdf.name, type_p, r.texte_normalise, r.nb_pages, r.avertissements))
    return out


def dce_concatene_pour(affaire: Affaire) -> str:
    """Concatène toutes les pièces du DCE de l'affaire en un seul texte balisé."""
    pieces = charger_pieces(affaire)
    return concatener_dce([(type_p, texte) for _, type_p, texte, _, _ in pieces])


def charger_analyse(affaire: Affaire) -> AnalyseAO | None:
    if not affaire.has_analyse():
        return None
    try:
        return AnalyseAO.model_validate(
            json.loads(affaire.analyse_path.read_text(encoding="utf-8"))
        )
    except Exception:
        return None


def charger_mt(affaire: Affaire) -> MemoireTechniqueGenere | None:
    if not affaire.has_mt():
        return None
    try:
        return MemoireTechniqueGenere.model_validate(
            json.loads(affaire.mt_json_path.read_text(encoding="utf-8"))
        )
    except Exception:
        return None


def charger_dpgf(affaire: Affaire) -> DPGFGeneree | None:
    if not affaire.has_dpgf():
        return None
    try:
        return DPGFGeneree.model_validate(
            json.loads(affaire.dpgf_json_path.read_text(encoding="utf-8"))
        )
    except Exception:
        return None


def charger_couverture(affaire: Affaire) -> RapportCouverture | None:
    if not affaire.has_couverture():
        return None
    try:
        return RapportCouverture.model_validate(
            json.loads(affaire.couverture_path.read_text(encoding="utf-8"))
        )
    except Exception:
        return None


def charger_synthese(affaire: Affaire) -> SyntheseDirection | None:
    if not affaire.has_synthese():
        return None
    try:
        return SyntheseDirection.model_validate(
            json.loads(affaire.synthese_json_path.read_text(encoding="utf-8"))
        )
    except Exception:
        return None


def charger_lettre(affaire: Affaire) -> LettrePresentation | None:
    if not affaire.lettre_json_path.exists():
        return None
    try:
        return LettrePresentation.model_validate(
            json.loads(affaire.lettre_json_path.read_text(encoding="utf-8"))
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Barre latérale : sélection / création d'affaire
# ---------------------------------------------------------------------------


def render_sidebar() -> Affaire | None:
    logo_url = _logo_data_url()
    if logo_url:
        st.sidebar.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 12px; margin: 0 0 0.25rem 0;">
                <img src="{logo_url}" width="56" height="56" alt="I2AO" style="flex-shrink: 0;"/>
                <h1 style="margin: 0; color: inherit; font-size: 2.2rem; font-family: 'Times New Roman', Georgia, serif; line-height: 1;">I2AO</h1>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.title("I2AO")
    st.sidebar.caption("Outil de réponse aux AO\nBET pathologie / consolidation")

    client = get_llm_client()
    if client is None:
        st.sidebar.error("⚠️ GOOGLE_API_KEY non configurée")
        st.sidebar.caption("Voir le fichier `.env` à la racine du projet.")
    else:
        if is_mode_presentation():
            st.sidebar.success("🤖 Connecté")
        else:
            st.sidebar.success(f"🤖 Connecté à `{LLM_MODEL}`")

    # Mode présentation toggle
    if "mode_presentation" not in st.session_state:
        st.session_state.mode_presentation = True
    st.session_state.mode_presentation = st.sidebar.toggle(
        "🎤 Mode présentation",
        value=is_mode_presentation(),
        help="Masque les détails techniques (tokens, slugs, debug) pour un pitch épuré.",
    )

    # Sélecteur de profil métier (bibliothèque MT + catalogue DPGF + bet-profile)
    profils_disponibles = lister_profils_disponibles()
    if profils_disponibles:
        if "profil_actif" not in st.session_state or st.session_state.profil_actif not in profils_disponibles:
            st.session_state.profil_actif = (
                PROFIL_ACTIF_DEFAUT
                if PROFIL_ACTIF_DEFAUT in profils_disponibles
                else profils_disponibles[0]
            )
        st.session_state.profil_actif = st.sidebar.selectbox(
            "🧰 Profil métier",
            options=profils_disponibles,
            index=profils_disponibles.index(st.session_state.profil_actif),
            help=(
                "Choisit la bibliothèque MT, le catalogue DPGF et le profil entreprise "
                "à utiliser. Pour ajouter un profil, créer un dossier sous "
                "content/profiles/<slug>/ avec mt-library/, dpgf-catalog/ et bet-profile.md."
            ),
        )

    st.sidebar.divider()

    # Init la démo automatiquement
    initialiser_demo_si_absente()

    affaires = lister_affaires()

    # Mode : single affaire vs vue comparative
    if "vue_active" not in st.session_state:
        st.session_state.vue_active = "affaire"

    options_vue = ["affaire", "comparaison", "profils"]
    libelles_vue = {
        "affaire": "📂 Une affaire",
        "comparaison": "📊 Comparaison",
        "profils": "🧰 Gestion des profils",
    }
    if st.session_state.vue_active not in options_vue:
        st.session_state.vue_active = "affaire"
    st.session_state.vue_active = st.sidebar.radio(
        "Vue",
        options=options_vue,
        format_func=lambda v: libelles_vue[v],
        index=options_vue.index(st.session_state.vue_active),
        label_visibility="collapsed",
    )

    st.sidebar.subheader("Affaires")
    if not affaires:
        st.sidebar.info("Aucune affaire pour l'instant.")
        affaire_active: Affaire | None = None
    else:
        slugs = [a.slug for a in affaires]
        labels = {a.slug: a.nom for a in affaires}

        if "active_slug" not in st.session_state or st.session_state.active_slug not in slugs:
            st.session_state.active_slug = slugs[0]

        st.session_state.active_slug = st.sidebar.radio(
            "Sélectionner une affaire",
            options=slugs,
            format_func=lambda s: labels[s],
            label_visibility="collapsed",
            disabled=(st.session_state.vue_active == "comparaison"),
        )
        affaire_active = get_affaire(st.session_state.active_slug)

    st.sidebar.divider()

    with st.sidebar.expander("➕ Nouvelle affaire", expanded=False):
        nom = st.text_input("Nom de l'opération", key="nouveau_nom")
        if st.button("Créer", key="btn_creer", use_container_width=True):
            if nom.strip():
                a = creer_affaire(nom.strip())
                st.session_state.active_slug = a.slug
                st.rerun()
            else:
                st.warning("Donnez un nom à l'affaire.")

    if affaire_active:
        with st.sidebar.expander("🗑️ Supprimer cette affaire", expanded=False):
            st.caption(f"Affaire : **{affaire_active.nom}**")
            if st.button(
                "Supprimer définitivement",
                type="secondary",
                key="btn_supprimer",
                use_container_width=True,
            ):
                supprimer_affaire(affaire_active.slug)
                st.session_state.pop("active_slug", None)
                st.rerun()

    # ----- Tracker de coût LLM -----
    st.sidebar.divider()
    usage = get_session_usage()
    if usage.nb_appels > 0:
        st.sidebar.markdown("##### 💰 Coût LLM session")
        cols = st.sidebar.columns(2)
        cols[0].metric("Appels", usage.nb_appels)
        cols[1].metric("Coût", f"${usage.cout_total_usd:.4f}")
        if not is_mode_presentation():
            with st.sidebar.expander("Détail des tokens", expanded=False):
                st.caption(f"Input : {usage.prompt_tokens:,} tk".replace(",", " "))
                st.caption(f"Cached : {usage.cached_tokens:,} tk".replace(",", " "))
                st.caption(f"Output : {usage.output_tokens:,} tk".replace(",", " "))
                st.caption(f"Thinking : {usage.thoughts_tokens:,} tk".replace(",", " "))
                st.caption(f"Tarifs Gemini 2.5 Flash, ≤ 128k context")
                if st.button("Réinitialiser le compteur", key="btn_reset_usage"):
                    reset_session_usage()
                    st.rerun()
    elif not is_mode_presentation():
        st.sidebar.caption("💰 Aucun appel LLM cette session.")

    return affaire_active


# ---------------------------------------------------------------------------
# Onglet Vue d'ensemble : dashboard visuel
# ---------------------------------------------------------------------------


def render_tab_overview(affaire: Affaire) -> None:
    st.header("Vue d'ensemble")

    analyse = charger_analyse(affaire)
    mt = charger_mt(affaire)
    dpgf = charger_dpgf(affaire)
    rapport = charger_couverture(affaire)
    synth = charger_synthese(affaire)

    if not analyse:
        st.info(
            "Lance l'analyse de l'AO dans l'onglet **🔍 Analyse** pour activer le tableau de bord."
        )
        return

    # Bandeau métriques principales
    cols = st.columns(5)
    cols[0].metric("Pièces DCE", len(list(affaire.pieces_dir.glob("*.pdf"))))
    cols[1].metric("Exigences", len(analyse.exigences))
    cols[2].metric(
        "Score MT",
        f"{rapport.score_pct:.0f}%" if rapport else "—",
    )
    cols[3].metric(
        "DQE HT",
        f"{dpgf.montant_dqe_he:,.0f} €".replace(",", " ") if dpgf else "—",
    )
    cols[4].metric("Date remise", analyse.date_remise[:30] if len(analyse.date_remise) > 30 else analyse.date_remise)

    st.divider()

    # Identité du marché en bandeau
    cols = st.columns([2, 3])
    with cols[0]:
        st.markdown("##### Identité")
        st.markdown(f"**Pouvoir adjudicateur** \n{analyse.pouvoir_adjudicateur}")
        st.markdown(f"**Type de marché** \n{analyse.type_marche}")
        st.markdown(f"**Typologie de mission** \n{analyse.typologie_mission}")
        st.markdown(f"**Matériau dominant** \n{analyse.materiau_dominant}")
        st.markdown(f"**Montant maximum HT** \n{analyse.montant_max_he}")
        st.markdown(f"**Durée** \n{analyse.duree}")

    with cols[1]:
        st.markdown("##### Recommandation Go / No-go")
        if synth:
            reco = synth.recommandation_go_nogo
            if "GO sous conditions" in reco or "GO conditionn" in reco:
                st.warning(reco)
            elif "NO-GO" in reco.upper():
                st.error(reco)
            else:
                st.success(reco)
        else:
            st.info("Génère la synthèse direction pour obtenir la recommandation.")

        st.markdown("##### Points d'attention business")
        for p in analyse.points_attention_majeurs[:5]:
            st.markdown(f"- {p}")

    st.divider()

    # Graphiques en deux colonnes
    cols = st.columns(2)
    with cols[0]:
        st.markdown("##### Répartition des exigences")
        st.plotly_chart(
            bar_exigences_par_importance(analyse.exigences),
            use_container_width=True,
            config={"displayModeBar": False},
            key=f"overview_bar_importance_{affaire.slug}",
        )
        st.plotly_chart(
            bar_exigences_par_categorie(analyse.exigences),
            use_container_width=True,
            config={"displayModeBar": False},
            key=f"overview_bar_categorie_{affaire.slug}",
        )

    with cols[1]:
        if rapport:
            st.markdown("##### Couverture du mémoire technique")
            st.plotly_chart(
                donut_couverture(
                    rapport.nb_couvertes,
                    rapport.nb_partiellement_couvertes,
                    rapport.nb_non_couvertes,
                    rapport.nb_non_applicables,
                    rapport.score_pct,
                ),
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"overview_donut_couverture_{affaire.slug}",
            )
        else:
            st.markdown("##### Couverture du mémoire technique")
            st.info("Évalue la couverture dans l'onglet 📝 Mémoire technique.")

        if dpgf and dpgf.dqe:
            st.markdown("##### Répartition du DQE par chapitre")
            st.plotly_chart(
                donut_repartition_dqe(dpgf.dqe, dpgf.montant_dqe_he),
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"overview_donut_dqe_{affaire.slug}",
            )
        else:
            st.markdown("##### Répartition du DQE")
            st.info("Génère la DPGF dans l'onglet 💰 DPGF.")

    st.divider()

    # ── Graphiques 3D WebGL ───────────────────────────────────────────────
    st.markdown("##### 🌐 Vue 3D des exigences — rotatif à la souris")
    st.caption("Chaque point = une exigence du DCE. Axes : catégorie × importance × rang. Interactif — clic + drag pour faire pivoter.")
    st.plotly_chart(
        scatter3d_exigences(analyse.exigences),
        use_container_width=True,
        config={"displayModeBar": True, "displaylogo": False},
        key=f"overview_scatter3d_{affaire.slug}",
    )

    if dpgf and dpgf.dqe:
        st.markdown("##### 🏔️ Paysage financier du DQE — surface 3D")
        st.caption("Chaque montagne = un chapitre du DQE. Hauteur proportionnelle au montant HT. Interactif — faire pivoter pour explorer.")
        st.plotly_chart(
            surface3d_dqe(dpgf.dqe),
            use_container_width=True,
            config={"displayModeBar": True, "displaylogo": False},
            key=f"overview_surface3d_{affaire.slug}",
        )


# ---------------------------------------------------------------------------
# Onglet DCE : upload + visualisation
# ---------------------------------------------------------------------------


def render_tab_dce(affaire: Affaire) -> None:
    st.header("📂 Pièces du DCE")

    uploaded = st.file_uploader(
        "Déposer une ou plusieurs pièces (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
        key=f"upload_{affaire.slug}",
    )
    if uploaded:
        cols = st.columns([1, 5])
        with cols[0]:
            if st.button("Importer", type="primary", use_container_width=True, key="btn_importer"):
                for f in uploaded:
                    ajouter_piece(affaire, f.name, f.getvalue())
                st.success(f"{len(uploaded)} fichier(s) importé(s).")
                st.rerun()

    pieces = charger_pieces(affaire)
    if not pieces:
        st.info("Aucune pièce déposée pour l'instant. Importez vos PDFs ci-dessus.")
        return

    total_pages = sum(nb for _, _, _, nb, _ in pieces)
    total_chars = sum(len(t) for _, _, t, _, _ in pieces)
    cols = st.columns(4)
    cols[0].metric("Pièces", len(pieces))
    cols[1].metric("Pages", total_pages)
    cols[2].metric("Caractères extraits", f"{total_chars:,}".replace(",", " "))
    types_uniques = {p[1] for p in pieces}
    cols[3].metric("Types détectés", len(types_uniques))

    # Avertissements globaux (PDF scannés notamment)
    warnings_globaux = [w for _, _, _, _, ws in pieces for w in ws]
    if warnings_globaux:
        for w in warnings_globaux:
            st.warning(f"⚠️ {w}")

    st.divider()

    for nom, type_p, texte, nb_pages, warnings in pieces:
        label = f"{piece_humaine(type_p)} — {nom}  ·  {nb_pages} pages"
        if warnings:
            label += "  ⚠️"
        with st.expander(label):
            for w in warnings:
                st.warning(w)
            st.text_area(
                "Texte extrait",
                texte[:5000] + ("\n\n[...]" if len(texte) > 5000 else ""),
                height=240,
                key=f"texte_{nom}",
                label_visibility="collapsed",
            )


# ---------------------------------------------------------------------------
# Onglet Analyse : extraction + visualisation
# ---------------------------------------------------------------------------


def render_tab_analyse(affaire: Affaire, client: LLMClient | None) -> None:
    st.header("🔍 Analyse du DCE")

    if not affaire.has_pieces():
        st.warning("Aucune pièce déposée. Va dans l'onglet **DCE** pour importer le dossier.")
        return

    if client is None:
        st.error("Clé API Gemini absente — impossible de lancer l'analyse.")
        return

    cols = st.columns([1, 1, 4])
    relancer = cols[0].button("Lancer l'analyse", type="primary", use_container_width=True)
    relancer_2 = cols[1].button(
        "Relancer", use_container_width=True, disabled=not affaire.has_analyse()
    )

    if relancer or relancer_2 or (not affaire.has_analyse() and "analyse_demande" in st.session_state):
        st.session_state.pop("analyse_demande", None)
        with st.status("Extraction en cours…", expanded=True) as status:
            st.write("Lecture des PDF…")
            dce = dce_concatene_pour(affaire)
            st.write(f"DCE concaténé : {len(dce):,} caractères")

            st.write(f"Appel Gemini ({LLM_MODEL})…")
            try:
                analyse = extraire_analyse_ao(client, dce)
            except LLMError as e:
                status.update(label="Échec de l'extraction", state="error", expanded=True)
                afficher_erreur_llm(e, "extraction du DCE")
                return
            affaire.analyse_path.write_text(
                analyse.model_dump_json(indent=2), encoding="utf-8"
            )
            u = client.last_usage
            msg = f"OK — {len(analyse.exigences)} exigences extraites"
            if not is_mode_presentation() and u:
                msg += (
                    f" · prompt={u.prompt_tokens} output={u.output_tokens} "
                    f"thinking={u.thoughts_tokens}"
                )
            st.write(msg)
            status.update(label="Analyse terminée", state="complete", expanded=False)

    analyse = charger_analyse(affaire)
    if analyse is None:
        st.info("Lance l'extraction pour voir l'analyse structurée du DCE.")
        return

    st.subheader("Identité du marché")
    cols = st.columns(2)
    with cols[0]:
        st.markdown(f"**Objet :** {analyse.objet_resume}")
        st.markdown(f"**Pouvoir adjudicateur :** {analyse.pouvoir_adjudicateur}")
        st.markdown(f"**Type de marché :** {analyse.type_marche}")
        st.markdown(f"**Typologie de mission :** {analyse.typologie_mission}")
        st.markdown(f"**Matériau dominant :** {analyse.materiau_dominant}")
    with cols[1]:
        st.markdown(f"**Montant max :** {analyse.montant_max_he}")
        st.markdown(f"**Durée :** {analyse.duree}")
        st.markdown(f"**Date limite remise :** {analyse.date_remise}")
        st.markdown(f"**Validité offre :** {analyse.delai_validite_offre}")

    st.subheader("Points d'attention majeurs")
    for p in analyse.points_attention_majeurs:
        st.markdown(f"- {p}")

    st.subheader(f"Exigences extraites ({len(analyse.exigences)})")
    cats = Counter(e.categorie for e in analyse.exigences)
    src = Counter(e.source_piece for e in analyse.exigences)

    # Distribution par importance — bar empilée
    st.plotly_chart(
        bar_exigences_par_importance(analyse.exigences),
        use_container_width=True,
        config={"displayModeBar": False},
        key=f"analyse_bar_importance_{affaire.slug}",
    )

    # Distribution par catégorie — bar horizontal
    cols_charts = st.columns(2)
    with cols_charts[0]:
        st.markdown("**Par catégorie**")
        st.plotly_chart(
            bar_exigences_par_categorie(analyse.exigences),
            use_container_width=True,
            config={"displayModeBar": False},
            key=f"analyse_bar_categorie_{affaire.slug}",
        )
    with cols_charts[1]:
        st.markdown("**Par source du DCE**")
        st.dataframe(
            {"Source": list(src.keys()), "Nombre": list(src.values())},
            use_container_width=True,
            hide_index=True,
            height=320,
        )

    filtre_imp = st.multiselect(
        "Filtrer par importance",
        options=["bloquant", "important", "mineur"],
        default=["bloquant", "important"],
    )
    filtre_cat = st.multiselect(
        "Filtrer par catégorie",
        options=sorted(cats.keys()),
        default=sorted(cats.keys()),
    )
    filtres_exigences = [
        e for e in analyse.exigences if e.importance in filtre_imp and e.categorie in filtre_cat
    ]

    st.dataframe(
        {
            "Importance": [e.importance for e in filtres_exigences],
            "Catégorie": [e.categorie for e in filtres_exigences],
            "Source": [e.source_piece for e in filtres_exigences],
            "Libellé": [e.libelle for e in filtres_exigences],
            "Détail": [e.detail for e in filtres_exigences],
        },
        use_container_width=True,
        height=420,
    )

    st.download_button(
        "⬇ Télécharger l'analyse complète (JSON)",
        data=affaire.analyse_path.read_bytes(),
        file_name=f"analyse-{affaire.slug}.json",
        mime="application/json",
    )


# ---------------------------------------------------------------------------
# Onglet Mémoire technique
# ---------------------------------------------------------------------------


def render_tab_mt(affaire: Affaire, client: LLMClient | None) -> None:
    st.header("📝 Mémoire technique")

    if not affaire.has_analyse():
        st.warning("Lance d'abord l'analyse de l'AO dans l'onglet **Analyse**.")
        return

    if client is None:
        st.error("Clé API Gemini absente — impossible de générer le MT.")
        return

    cols = st.columns([1, 1, 4])
    generer_btn = cols[0].button("Générer le MT", type="primary", use_container_width=True)
    regenerer_btn = cols[1].button(
        "Regénérer", use_container_width=True, disabled=not affaire.has_mt()
    )

    if generer_btn or regenerer_btn:
        analyse = charger_analyse(affaire)
        with st.status("Génération du mémoire technique…", expanded=True) as status:
            st.write(f"Appel Gemini ({LLM_MODEL}) avec bibliothèque MT + profil entreprise…")
            try:
                mt = generer_mt(client, analyse, profil=get_profil_actif())
            except LLMError as e:
                status.update(label="Échec de la génération MT", state="error", expanded=True)
                afficher_erreur_llm(e, "génération du mémoire technique")
                return
            affaire.mt_json_path.write_text(
                mt.model_dump_json(indent=2), encoding="utf-8"
            )
            u = client.last_usage
            msg = f"OK — {len(mt.sections)} sections"
            if not is_mode_presentation() and u:
                msg += (
                    f" · prompt={u.prompt_tokens} output={u.output_tokens} "
                    f"thinking={u.thoughts_tokens}"
                )
            st.write(msg)

            orphelines = detecter_variables_non_remplies(mt)
            if orphelines:
                st.warning(f"{len(orphelines)} sections avec variables non remplies.")
            else:
                st.write("Aucune variable {{...}} orpheline.")

            st.write("Export DOCX…")
            exporter_mt_docx(mt, affaire.mt_docx_path)
            st.write(f"DOCX produit ({affaire.mt_docx_path.stat().st_size / 1024:.1f} KB)")
            status.update(label="MT généré", state="complete", expanded=False)

    mt = charger_mt(affaire)
    if mt is None:
        st.info("Génère le MT pour voir l'aperçu et le télécharger.")
        return

    cols = st.columns(2)
    cols[0].metric("Sections", len(mt.sections))
    cols[1].metric("Pondération valeur technique attendue", "60%")

    st.subheader("Aperçu")
    for s in mt.sections:
        with st.expander(f"{s.titre}" + (f" — {s.sous_titre}" if s.sous_titre else "")):
            st.markdown(s.contenu_md)

    if affaire.mt_docx_path.exists():
        st.download_button(
            "⬇ Télécharger le mémoire technique (DOCX)",
            data=affaire.mt_docx_path.read_bytes(),
            file_name=f"memoire-technique-{affaire.slug}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
        )

    # ----- Score de couverture -----
    st.divider()
    st.subheader("🎯 Score de couverture du MT")
    st.caption(
        "Vérifie pour chaque exigence importante du DCE si le MT la traite. "
        "Met en évidence les exigences applicables non couvertes."
    )

    cols = st.columns([1, 1, 4])
    eval_btn = cols[0].button(
        "Évaluer la couverture", key="btn_eval_cov", use_container_width=True
    )
    reeval_btn = cols[1].button(
        "Ré-évaluer",
        key="btn_reeval_cov",
        use_container_width=True,
        disabled=not affaire.has_couverture(),
    )

    if eval_btn or reeval_btn:
        analyse = charger_analyse(affaire)
        if analyse is None or mt is None:
            st.error("Analyse ou MT manquant.")
        else:
            with st.status("Évaluation en cours…", expanded=True) as status:
                st.write(
                    f"Appel Gemini ({LLM_MODEL}) sur les exigences bloquantes et importantes…"
                )
                try:
                    rapport = evaluer_couverture(client, analyse, mt)
                except LLMError as e:
                    status.update(label="Échec de l'évaluation", state="error", expanded=True)
                    afficher_erreur_llm(e, "évaluation de la couverture")
                    return
                affaire.couverture_path.write_text(
                    rapport.model_dump_json(indent=2), encoding="utf-8"
                )
                u = client.last_usage
                msg = (
                    f"OK — score {rapport.score_pct:.0f}% sur "
                    f"{rapport.nb_total_evaluees - rapport.nb_non_applicables} exigences applicables"
                )
                if not is_mode_presentation() and u:
                    msg += (
                        f" · prompt={u.prompt_tokens} output={u.output_tokens} "
                        f"thinking={u.thoughts_tokens}"
                    )
                st.write(msg)
                status.update(label="Couverture évaluée", state="complete", expanded=False)

    rapport = charger_couverture(affaire)
    if rapport is None:
        st.info("Lance l'évaluation pour voir le score de couverture.")
        return

    cols = st.columns([1, 1])
    with cols[0]:
        st.plotly_chart(
            gauge_score(rapport.score_pct, "Score de couverture"),
            use_container_width=True,
            config={"displayModeBar": False},
            key=f"mt_gauge_{affaire.slug}",
        )
    with cols[1]:
        st.plotly_chart(
            donut_couverture(
                rapport.nb_couvertes,
                rapport.nb_partiellement_couvertes,
                rapport.nb_non_couvertes,
                rapport.nb_non_applicables,
                rapport.score_pct,
            ),
            use_container_width=True,
            config={"displayModeBar": False},
            key=f"mt_donut_couverture_{affaire.slug}",
        )

    st.markdown(f"_{rapport.synthese}_")

    # Mise en avant des exigences non couvertes
    non_couvertes = [d for d in rapport.details if d.statut == "non-couverte"]
    if non_couvertes:
        st.warning(f"⚠️ {len(non_couvertes)} exigence(s) applicable(s) au MT non couverte(s) :")
        for d in non_couvertes:
            st.markdown(f"- **[{d.importance}/{d.categorie}]** {d.exigence_libelle} — _{d.commentaire}_")

    # Détail pliable
    with st.expander("Voir le détail par exigence"):
        statut_filtre = st.multiselect(
            "Filtrer par statut",
            options=["couverte", "partiellement-couverte", "non-couverte", "non-applicable"],
            default=["couverte", "partiellement-couverte", "non-couverte", "non-applicable"],
            key="filtre_statut_cov",
        )
        details = [d for d in rapport.details if d.statut in statut_filtre]
        st.dataframe(
            {
                "Statut": [d.statut for d in details],
                "Importance": [d.importance for d in details],
                "Catégorie": [d.categorie for d in details],
                "Exigence": [d.exigence_libelle for d in details],
                "Section MT": [d.section_mt_id or "" for d in details],
                "Commentaire": [d.commentaire for d in details],
            },
            use_container_width=True,
            height=380,
        )


# ---------------------------------------------------------------------------
# Onglet DPGF
# ---------------------------------------------------------------------------


def render_tab_dpgf(affaire: Affaire, client: LLMClient | None) -> None:
    st.header("💰 DPGF — BPU rempli + DQE chiffré")

    if not affaire.has_analyse():
        st.warning("Lance d'abord l'analyse de l'AO dans l'onglet **Analyse**.")
        return

    if client is None:
        st.error("Clé API Gemini absente — impossible de générer la DPGF.")
        return

    cols = st.columns([1, 1, 4])
    generer_btn = cols[0].button(
        "Générer la DPGF", type="primary", use_container_width=True, key="btn_gen_dpgf"
    )
    regenerer_btn = cols[1].button(
        "Regénérer",
        use_container_width=True,
        disabled=not affaire.has_dpgf(),
        key="btn_regen_dpgf",
    )

    if generer_btn or regenerer_btn:
        analyse = charger_analyse(affaire)
        dce = dce_concatene_pour(affaire)

        with st.status("Génération de la DPGF…", expanded=True) as status:
            st.write(f"Appel Gemini ({LLM_MODEL}) pour le programme indicatif…")
            try:
                dpgf = generer_dpgf(client, analyse, dce, profil=get_profil_actif())
            except LLMError as e:
                status.update(label="Échec de la génération DPGF", state="error", expanded=True)
                afficher_erreur_llm(e, "génération DPGF")
                return
            affaire.dpgf_json_path.write_text(
                dpgf.model_dump_json(indent=2), encoding="utf-8"
            )
            st.write(
                f"OK — {len(dpgf.bpu)} prestations · {len(dpgf.dqe)} lignes DQE · "
                f"montant {dpgf.montant_dqe_he:,.2f} € HT".replace(",", " ")
            )

            st.write("Export XLSX…")
            exporter_dpgf_xlsx(
                dpgf,
                affaire.dpgf_xlsx_path,
                marche_ref="2026-MOE-STRUCT-01",
                candidat=CANDIDAT_NOM,
            )
            st.write(f"XLSX produit ({affaire.dpgf_xlsx_path.stat().st_size / 1024:.1f} KB)")
            status.update(label="DPGF générée", state="complete", expanded=False)

    dpgf = charger_dpgf(affaire)
    if dpgf is None:
        st.info("Génère la DPGF pour voir le BPU + DQE chiffré.")
        return

    cols = st.columns(3)
    cols[0].metric("Prestations BPU", len(dpgf.bpu))
    cols[1].metric("Lignes DQE", len(dpgf.dqe))
    cols[2].metric("Total DQE HT", f"{dpgf.montant_dqe_he:,.0f} €".replace(",", " "))

    st.caption(f"**Programme indicatif :** {dpgf.description_programme}")

    if dpgf.dqe:
        cols_charts = st.columns([3, 4])
        with cols_charts[0]:
            st.plotly_chart(
                donut_repartition_dqe(dpgf.dqe, dpgf.montant_dqe_he),
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"dpgf_donut_{affaire.slug}",
            )
        with cols_charts[1]:
            st.plotly_chart(
                bar_dqe_par_categorie(dpgf.dqe),
                use_container_width=True,
                config={"displayModeBar": False},
                key=f"dpgf_bar_{affaire.slug}",
            )

    tab_dqe, tab_bpu = st.tabs(["📊 DQE chiffré", "📋 BPU complet"])

    with tab_dqe:
        st.dataframe(
            {
                "Code": [l.code for l in dpgf.dqe],
                "Catégorie": [l.categorie for l in dpgf.dqe],
                "Désignation": [l.libelle for l in dpgf.dqe],
                "Unité": [l.unite for l in dpgf.dqe],
                "Quantité": [l.quantite for l in dpgf.dqe],
                "PU HT": [l.prix_unitaire for l in dpgf.dqe],
                "Montant HT": [l.montant for l in dpgf.dqe],
                "Justification": [l.justification or "" for l in dpgf.dqe],
            },
            use_container_width=True,
            height=420,
        )

    with tab_bpu:
        st.dataframe(
            {
                "Code": [p.code for p in dpgf.bpu],
                "Catégorie": [p.categorie for p in dpgf.bpu],
                "Désignation": [p.libelle for p in dpgf.bpu],
                "Unité": [p.unite for p in dpgf.bpu],
                "Prix unitaire HT": [p.prix_unitaire for p in dpgf.bpu],
            },
            use_container_width=True,
            height=420,
        )

    if affaire.dpgf_xlsx_path.exists():
        st.download_button(
            "⬇ Télécharger la DPGF (XLSX)",
            data=affaire.dpgf_xlsx_path.read_bytes(),
            file_name=f"dpgf-{affaire.slug}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )


# ---------------------------------------------------------------------------
# Onglet Go / No-go : synthèse direction
# ---------------------------------------------------------------------------


def render_tab_synthese(affaire: Affaire, client: LLMClient | None) -> None:
    st.header("📊 Synthèse direction — Go / No-go")
    st.caption(
        "1-pager destiné à un dirigeant : faits clés + atouts spécifiques + risques + "
        "recommandation argumentée. Rédigé en croisant l'analyse de l'AO avec le profil entreprise."
    )

    if not affaire.has_analyse():
        st.warning("Lance d'abord l'analyse de l'AO dans l'onglet **Analyse**.")
        return

    if client is None:
        st.error("Clé API Gemini absente.")
        return

    cols = st.columns([1, 1, 4])
    generer_btn = cols[0].button(
        "Générer la synthèse", type="primary", use_container_width=True, key="btn_gen_syn"
    )
    regenerer_btn = cols[1].button(
        "Regénérer",
        use_container_width=True,
        disabled=not affaire.has_synthese(),
        key="btn_regen_syn",
    )

    if generer_btn or regenerer_btn:
        analyse = charger_analyse(affaire)
        mt = charger_mt(affaire)
        dpgf = charger_dpgf(affaire)
        with st.status("Génération de la synthèse…", expanded=True) as status:
            st.write(f"Appel Gemini ({LLM_MODEL})…")
            try:
                synth = generer_synthese(client, analyse, mt, dpgf, profil=get_profil_actif())
            except LLMError as e:
                status.update(label="Échec de la synthèse", state="error", expanded=True)
                afficher_erreur_llm(e, "génération de la synthèse direction")
                return
            affaire.synthese_json_path.write_text(
                synth.model_dump_json(indent=2), encoding="utf-8"
            )
            u = client.last_usage
            msg = (
                f"OK — {len(synth.atouts_candidat)} atouts · "
                f"{len(synth.risques_principaux)} risques"
            )
            if not is_mode_presentation() and u:
                msg += (
                    f" · prompt={u.prompt_tokens} output={u.output_tokens} "
                    f"thinking={u.thoughts_tokens}"
                )
            st.write(msg)

            st.write("Export DOCX 1-pager…")
            exporter_synthese_docx(synth, affaire.synthese_docx_path, candidat=CANDIDAT_NOM)
            st.write(f"DOCX produit ({affaire.synthese_docx_path.stat().st_size / 1024:.1f} KB)")
            status.update(label="Synthèse générée", state="complete", expanded=False)

    synth = charger_synthese(affaire)
    if synth is None:
        st.info("Génère la synthèse pour voir le 1-pager Go / No-go.")
        return

    # Identification du marché
    st.subheader("Identification du marché")
    cols = st.columns(2)
    with cols[0]:
        st.markdown(f"**Objet :** {synth.titre_operation}")
        st.markdown(f"**Pouvoir adjudicateur :** {synth.pouvoir_adjudicateur}")
        st.markdown(f"**Type de marché :** {synth.type_marche}")
    with cols[1]:
        st.markdown(f"**Montant maximum HT :** {synth.montant_max_he}")
        st.markdown(f"**Durée :** {synth.duree}")
        st.markdown(f"**Date limite remise :** {synth.date_remise}")

    st.subheader("Critères de jugement")
    for c in synth.criteres_jugement:
        st.markdown(f"- **{c.libelle}** — {c.ponderation}")

    cols = st.columns(2)
    with cols[0]:
        st.subheader("✅ Atouts du candidat sur cet AO")
        for a in synth.atouts_candidat:
            st.markdown(f"- {a}")
    with cols[1]:
        st.subheader("⚠️ Risques et points de vigilance")
        for r in synth.risques_principaux:
            st.markdown(f"- {r}")

    st.subheader("🎯 Points d'attention business")
    for p in synth.points_attention_business:
        st.markdown(f"- {p}")

    st.subheader("💰 Chiffrage prévisionnel")
    st.markdown(f"**Montant DQE estimé :** {synth.montant_dqe_estime_he}")

    st.divider()
    st.subheader("Recommandation")
    st.success(synth.recommandation_go_nogo)

    if affaire.synthese_docx_path.exists():
        st.download_button(
            "⬇ Télécharger le 1-pager Direction (DOCX)",
            data=affaire.synthese_docx_path.read_bytes(),
            file_name=f"synthese-direction-{affaire.slug}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
        )


# ---------------------------------------------------------------------------
# Onglet Pack candidature : lettre de présentation + ZIP final
# ---------------------------------------------------------------------------


def render_tab_candidature(affaire: Affaire, client: LLMClient | None) -> None:
    st.header("📦 Pack candidature")
    st.caption(
        "Lettre de présentation auto-générée + ZIP des pièces de la candidature, "
        "prêt à transmettre au pouvoir adjudicateur."
    )

    if not affaire.has_analyse():
        st.warning("Lance d'abord l'analyse de l'AO dans l'onglet **Analyse**.")
        return

    if client is None:
        st.error("Clé API Gemini absente.")
        return

    cols = st.columns([1, 1, 4])
    generer_btn = cols[0].button(
        "Générer la lettre", type="primary", use_container_width=True, key="btn_gen_lettre"
    )
    regenerer_btn = cols[1].button(
        "Regénérer",
        use_container_width=True,
        disabled=not affaire.lettre_json_path.exists(),
        key="btn_regen_lettre",
    )

    if generer_btn or regenerer_btn:
        analyse = charger_analyse(affaire)
        with st.status("Génération de la lettre…", expanded=True) as status:
            st.write(f"Appel Gemini ({LLM_MODEL})…")
            try:
                lettre = generer_lettre(
                    client, analyse, candidat=CANDIDAT_NOM, profil=get_profil_actif()
                )
            except LLMError as e:
                status.update(label="Échec de la lettre", state="error", expanded=True)
                afficher_erreur_llm(e, "génération de la lettre de présentation")
                return
            affaire.lettre_json_path.write_text(
                lettre.model_dump_json(indent=2), encoding="utf-8"
            )
            u = client.last_usage
            if is_mode_presentation() or not u:
                st.write("OK — lettre générée.")
            else:
                st.write(
                    f"OK — prompt={u.prompt_tokens} output={u.output_tokens} "
                    f"thinking={u.thoughts_tokens}"
                )

            st.write("Export DOCX…")
            exporter_lettre_docx(lettre, affaire.lettre_docx_path)
            st.write(f"DOCX produit ({affaire.lettre_docx_path.stat().st_size / 1024:.1f} KB)")
            status.update(label="Lettre générée", state="complete", expanded=False)

    lettre = charger_lettre(affaire)

    if lettre is None:
        st.info("Génère la lettre pour assembler le pack.")
    else:
        st.subheader("Aperçu de la lettre")
        with st.expander("En-tête et destinataire", expanded=False):
            cols = st.columns(2)
            cols[0].markdown("**Expéditeur**")
            cols[0].text(lettre.en_tete_candidat)
            cols[1].markdown("**Destinataire**")
            cols[1].text(lettre.destinataire_bloc)
            st.caption(f"Lieu et date : {lettre.lieu_date}")

        st.markdown(f"**{lettre.objet}**")
        st.markdown("_Madame, Monsieur,_")
        st.markdown(lettre.introduction)
        st.markdown(lettre.presentation_candidat)
        st.markdown(lettre.atouts_specifiques)

        st.markdown("**Pièces jointes :**")
        for piece in lettre.pieces_jointes:
            st.markdown(f"- {piece}")

        st.markdown(f"_{lettre.formule_politesse}_")
        st.markdown(f"**{lettre.signataire_nom}**  \n_{lettre.signataire_qualite}_")

        if affaire.lettre_docx_path.exists():
            st.download_button(
                "⬇ Télécharger la lettre seule (DOCX)",
                data=affaire.lettre_docx_path.read_bytes(),
                file_name=f"lettre-presentation-{affaire.slug}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="dl_lettre_seule",
            )

    st.divider()

    # ----- Pack ZIP -----
    st.subheader("📦 Pack candidature complet")
    pieces_pack = []
    if affaire.lettre_docx_path.exists():
        pieces_pack.append("01-Lettre-presentation.docx")
    if affaire.mt_docx_path.exists():
        pieces_pack.append("02-Memoire-technique.docx")
    if affaire.dpgf_xlsx_path.exists():
        pieces_pack.append("03-DPGF.xlsx")
    if affaire.synthese_docx_path.exists():
        pieces_pack.append("99-Synthese-direction (interne).docx")

    if not pieces_pack:
        st.info("Le pack sera disponible dès que tu auras généré au moins le MT ou la DPGF.")
        return

    st.markdown("**Contenu du pack :**")
    for p in pieces_pack:
        st.markdown(f"- {p}")

    cols = st.columns([1, 4])
    with cols[0]:
        if st.button(
            "Assembler le ZIP",
            type="primary",
            use_container_width=True,
            key="btn_assembler_pack",
        ):
            zip_path = creer_pack_zip(affaire, candidat=CANDIDAT_NOM)
            st.success(f"ZIP créé ({zip_path.stat().st_size / 1024:.1f} KB)")

    if affaire.pack_zip_path.exists():
        st.download_button(
            "⬇ Télécharger le pack candidature (ZIP)",
            data=affaire.pack_zip_path.read_bytes(),
            file_name=f"pack-candidature-{affaire.slug}.zip",
            mime="application/zip",
            type="primary",
            key="dl_pack_zip",
        )


# ---------------------------------------------------------------------------
# Vue principale
# ---------------------------------------------------------------------------


def render_landing() -> None:
    """Page d'accueil quand aucune affaire n'est sélectionnée."""
    logo_url = _logo_data_url()
    logo_block = (
        f'<img src="{logo_url}" width="110" height="110" alt="I2AO" '
        f'style="flex-shrink: 0; border-radius: 14px;"/>'
        if logo_url
        else ""
    )
    st.markdown(
        f"""
        <div class="i2ao-hero">
            <div style="display: flex; align-items: center; gap: 28px;">
                {logo_block}
                <div>
                    <h1>I2AO</h1>
                    <p>Outil de réponse aux appels d'offres pour bureau d'études structures, \
calibré pour le créneau pathologie / diagnostic / confortement.</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    with cols[0]:
        st.markdown("### 🔍 Analyse du DCE")
        st.markdown(
            "Identification automatique de l'identité du marché et extraction structurée "
            "de **70 à 80 exigences** classées par importance, catégorie et source."
        )
    with cols[1]:
        st.markdown("### 📝 Mémoire technique")
        st.markdown(
            "Assemblage en un seul appel LLM des **14 paragraphes** de la bibliothèque "
            "métier, contextualisés sur l'AO et la structure entreprise. Export DOCX prêt."
        )
    with cols[2]:
        st.markdown("### 💰 DPGF chiffrée")
        st.markdown(
            "Identification du programme indicatif depuis le CCTP et chiffrage automatique "
            "via le **catalogue de prestations** (BPU + DQE + récap par chapitre)."
        )

    st.divider()

    cols = st.columns(2)
    with cols[0]:
        st.markdown("### 🎯 Score de couverture")
        st.markdown(
            "Pour chaque exigence bloquante du DCE, l'outil vérifie si le mémoire technique "
            "la couvre. Affichage du score, identification des **exigences applicables non "
            "traitées**. L'outil vérifie sa propre conformité."
        )
    with cols[1]:
        st.markdown("### 📊 Synthèse direction Go/No-go")
        st.markdown(
            "1-pager pour un dirigeant pressé : faits clés + atouts spécifiques croisés "
            "AO × profil entreprise + risques + recommandation argumentée. **30 secondes "
            "pour décider d'engager ou non**."
        )

    st.info(
        "👈 Sélectionne une affaire dans la barre latérale, ou crée-en une nouvelle pour "
        "déposer un DCE."
    )


def render_status_line(affaire: Affaire) -> None:
    """Affiche la ligne d'état d'avancement d'une affaire."""
    items = [
        ("DCE", affaire.has_pieces()),
        ("Analyse", affaire.has_analyse()),
        ("MT", affaire.has_mt()),
        ("DPGF", affaire.has_dpgf()),
        ("Couverture", affaire.has_couverture()),
        ("Synthèse", affaire.has_synthese()),
    ]
    parts = []
    for label, ok in items:
        if ok:
            parts.append(f'<span class="ok">✓ {label}</span>')
        else:
            parts.append(f'<span class="ko">○ {label}</span>')
    html = '<div class="i2ao-status-line">' + "  ·  ".join(parts) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_comparaison() -> None:
    """Vue comparative entre toutes les affaires existantes."""
    st.title("📊 Vue comparative")
    st.caption(
        "Compare les affaires en cours pour arbitrer les priorités. Pratique pour un "
        "dév co qui doit choisir où concentrer la cellule réponse aux AO."
    )

    affaires = lister_affaires()
    if len(affaires) < 1:
        st.info("Aucune affaire à comparer.")
        return
    if len(affaires) == 1:
        st.info("Une seule affaire — la vue comparative devient utile à partir de 2 affaires.")

    # On charge les artefacts pour chaque affaire (sans appels LLM)
    data = []
    for a in affaires:
        analyse = charger_analyse(a)
        dpgf = charger_dpgf(a)
        rapport = charger_couverture(a)
        synth = charger_synthese(a)
        data.append({"affaire": a, "analyse": analyse, "dpgf": dpgf, "rapport": rapport, "synth": synth})

    st.subheader("Identité des marchés")
    cols = st.columns(len(data))
    for col, d in zip(cols, data):
        a = d["affaire"]
        analyse = d["analyse"]
        with col:
            st.markdown(f"### {a.nom.split('—')[0].strip()}")
            if analyse:
                st.markdown(f"**Type :** {analyse.type_marche}")
                st.markdown(f"**Montant max :** {analyse.montant_max_he}")
                st.markdown(f"**Durée :** {analyse.duree}")
                st.markdown(f"**Date remise :** {analyse.date_remise}")
            else:
                st.markdown("_Analyse non lancée_")

    st.subheader("Métriques comparées")

    # Graphique comparatif (KPIs entre affaires)
    if any(d["analyse"] for d in data):
        labels_aff = [d["affaire"].nom.split("—")[0].strip()[:35] for d in data]
        metriques = {
            "Exigences extraites": [
                len(d["analyse"].exigences) if d["analyse"] else 0 for d in data
            ],
            "Score couverture (%)": [
                d["rapport"].score_pct if d["rapport"] else 0 for d in data
            ],
            "Atouts candidat": [
                len(d["synth"].atouts_candidat) if d["synth"] else 0 for d in data
            ],
            "Risques identifiés": [
                len(d["synth"].risques_principaux) if d["synth"] else 0 for d in data
            ],
        }
        st.plotly_chart(
            bar_comparatif(labels_aff, metriques),
            use_container_width=True,
            config={"displayModeBar": False},
            key="comparaison_bar_kpi",
        )

    cols = st.columns(len(data))
    for col, d in zip(cols, data):
        a = d["affaire"]
        with col:
            st.markdown(f"**{a.slug}**")
            sub = st.columns(2)
            sub[0].metric("Exigences", len(d["analyse"].exigences) if d["analyse"] else "—")
            sub[1].metric(
                "Couverture",
                f"{d['rapport'].score_pct:.0f}%" if d["rapport"] else "—",
            )
            sub = st.columns(2)
            if d["dpgf"]:
                sub[0].metric(
                    "DQE HT",
                    f"{d['dpgf'].montant_dqe_he:,.0f} €".replace(",", " "),
                )
            else:
                sub[0].metric("DQE HT", "—")
            if d["synth"] and d["synth"].atouts_candidat:
                sub[1].metric("Atouts", len(d["synth"].atouts_candidat))
            else:
                sub[1].metric("Atouts", "—")

    st.divider()
    st.subheader("Recommandations Go / No-go")
    cols = st.columns(len(data))
    for col, d in zip(cols, data):
        a = d["affaire"]
        with col:
            st.markdown(f"**{a.nom.split('—')[0].strip()}**")
            if d["synth"]:
                # Le verdict en gros
                reco = d["synth"].recommandation_go_nogo
                if "GO sous conditions" in reco or "GO conditionn" in reco:
                    st.warning(reco)
                elif "NO-GO" in reco.upper():
                    st.error(reco)
                else:
                    st.success(reco)
            else:
                st.info("Synthèse non générée")

    st.divider()
    st.subheader("Atouts spécifiques par affaire")
    cols = st.columns(len(data))
    for col, d in zip(cols, data):
        a = d["affaire"]
        with col:
            st.markdown(f"**{a.nom.split('—')[0].strip()}**")
            if d["synth"] and d["synth"].atouts_candidat:
                for at in d["synth"].atouts_candidat[:5]:
                    st.markdown(f"- {at}")
            else:
                st.markdown("_Synthèse non générée_")

    st.subheader("Risques principaux par affaire")
    cols = st.columns(len(data))
    for col, d in zip(cols, data):
        a = d["affaire"]
        with col:
            st.markdown(f"**{a.nom.split('—')[0].strip()}**")
            if d["synth"] and d["synth"].risques_principaux:
                for r in d["synth"].risques_principaux[:5]:
                    st.markdown(f"- {r}")
            else:
                st.markdown("_Synthèse non générée_")


def render_profils_admin() -> None:
    """Page de gestion des profils métier : listing, création, import/export ZIP."""
    st.title("🧰 Gestion des profils métier")
    st.caption(
        "Un profil = une combinaison de bibliothèque MT + catalogue DPGF + profil entreprise, "
        "calibrée pour un type de BET. Tu peux en créer, importer un ZIP, exporter, supprimer."
    )

    # ----- Liste des profils existants -----
    st.subheader("Profils disponibles")
    stats = lister_profils_avec_stats()
    if not stats:
        st.info("Aucun profil pour l'instant. Crée-en un ci-dessous.")
    else:
        for p in stats:
            with st.container(border=True):
                cols = st.columns([3, 1, 1, 1, 1, 1])
                with cols[0]:
                    st.markdown(f"### `{p.slug}`")
                    if p.profil_template:
                        st.caption("⚠️ Profil template — `bet-profile.md` contient encore des `[À RENSEIGNER]`")
                    else:
                        st.caption("✓ Profil rempli")
                cols[1].metric("MT", p.nb_paragraphes)
                cols[2].metric("DPGF", p.nb_prestations)
                cols[3].metric("Taille", f"{p.taille_octets / 1024:.0f} KB")

                with cols[4]:
                    try:
                        zip_bytes = exporter_profil_zip(p.slug)
                        st.download_button(
                            "📦 ZIP",
                            data=zip_bytes,
                            file_name=f"profil-{p.slug}.zip",
                            mime="application/zip",
                            key=f"export_{p.slug}",
                            use_container_width=True,
                        )
                    except Exception as e:
                        st.caption(f"Export KO : {e}")

                with cols[5]:
                    if st.button(
                        "🗑️",
                        key=f"del_{p.slug}",
                        use_container_width=True,
                        help=f"Supprimer le profil {p.slug}",
                    ):
                        st.session_state[f"_confirm_del_{p.slug}"] = True

                if st.session_state.get(f"_confirm_del_{p.slug}"):
                    st.warning(f"Confirmer la suppression de **{p.slug}** ? Action irréversible.")
                    cc = st.columns([1, 1, 4])
                    if cc[0].button("Oui, supprimer", type="primary", key=f"del_yes_{p.slug}"):
                        try:
                            supprimer_profil(p.slug)
                            st.session_state.pop(f"_confirm_del_{p.slug}", None)
                            if st.session_state.get("profil_actif") == p.slug:
                                st.session_state.pop("profil_actif", None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Échec : {e}")
                    if cc[1].button("Annuler", key=f"del_no_{p.slug}"):
                        st.session_state.pop(f"_confirm_del_{p.slug}", None)
                        st.rerun()

    st.divider()

    # ----- Wizard de création -----
    st.subheader("✨ Créer un nouveau profil")
    with st.form("form_creer_profil"):
        cols = st.columns([1, 1])
        slug_nouveau = cols[0].text_input(
            "Slug du profil",
            help="Identifiant URL-friendly. Minuscules, chiffres, tirets. Ex : 'fluides-thermique'.",
            placeholder="ex : ma-specialite",
        )
        specialite = cols[1].text_input(
            "Nom de la spécialité",
            help="Affiché dans les templates générés.",
            placeholder="ex : BET fluides et thermique",
        )

        cols = st.columns([2, 1])
        slugs_existants = [p.slug for p in stats]
        copier_depuis = cols[0].selectbox(
            "Démarrer depuis…",
            options=["(profil vierge avec templates)"] + slugs_existants,
            help="Soit on génère des fichiers vierges (avec marqueurs [À RENSEIGNER]), "
            "soit on duplique un profil existant qu'on adaptera.",
        )

        submitted = st.form_submit_button("Créer le profil", type="primary")

        if submitted:
            if not slug_nouveau:
                st.error("Slug obligatoire.")
            elif not slug_valide(slug_nouveau):
                st.error(
                    "Slug invalide : doit commencer par une lettre, contenir uniquement "
                    "minuscules / chiffres / tirets, 2 à 50 caractères."
                )
            elif not specialite:
                st.error("Spécialité obligatoire.")
            else:
                copier = (
                    copier_depuis
                    if copier_depuis != "(profil vierge avec templates)"
                    else None
                )
                try:
                    target = creer_profil(slug_nouveau, specialite, copier_depuis=copier)
                    st.success(
                        f"✓ Profil **`{slug_nouveau}`** créé sous "
                        f"`{target.relative_to(target.parents[2])}`. "
                        "Édite les fichiers markdown / YAML pour le calibrer à ton métier, "
                        "puis sélectionne-le dans la sidebar."
                    )
                    if copier:
                        st.info(f"Copié depuis le profil **{copier}**.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

    st.divider()

    # ----- Import ZIP -----
    st.subheader("📥 Importer un profil depuis un ZIP")
    st.caption(
        "Le ZIP doit contenir un seul dossier racine au format produit par l'export "
        "(`<slug>/bet-profile.md` + `<slug>/mt-library/` + `<slug>/dpgf-catalog/`)."
    )
    cols = st.columns([2, 1])
    uploaded = cols[0].file_uploader(
        "Fichier ZIP du profil",
        type=["zip"],
        key="import_profil_zip",
    )
    slug_import = cols[1].text_input(
        "Slug cible (optionnel)",
        help="Pour renommer le profil à l'import. Laisser vide pour conserver le slug du ZIP.",
        placeholder="optionnel",
    )

    if uploaded is not None and st.button("Importer", type="primary", key="btn_importer_profil"):
        try:
            slug_resultant = importer_profil_zip(
                uploaded.getvalue(),
                slug_cible=slug_import.strip() or None,
            )
            st.success(f"✓ Profil **`{slug_resultant}`** importé. Disponible immédiatement dans la sidebar.")
            st.rerun()
        except (ValueError, RuntimeError) as e:
            st.error(f"Échec import : {e}")

    st.divider()

    # ----- Conseils persistance -----
    with st.expander("ℹ️ À propos de la persistance des profils créés ici"):
        st.markdown(
            """
            **Le filesystem de l'app déployée (Streamlit Cloud) est éphémère.** Tout profil créé
            ou importé via cette interface vit dans le container Streamlit jusqu'au prochain
            redéploiement (push GitHub, reboot, mise en veille prolongée).

            Pour persister un profil que tu viens de créer :

            1. **Télécharge son ZIP** via le bouton 📦 dans la liste ci-dessus
            2. **Dézippe-le** dans `content/profiles/` de ton fork local du repo
            3. **Commite + push** sur GitHub → Streamlit Cloud redéploie avec le profil persistant

            Si tu utilises l'app **en local** (`streamlit run`), aucun problème — les profils
            créés sont sauvegardés sur ton disque tant que tu ne supprimes pas le dossier.
            """
        )


def render_main(affaire: Affaire | None) -> None:
    if st.session_state.get("vue_active") == "comparaison":
        render_comparaison()
        return

    if st.session_state.get("vue_active") == "profils":
        render_profils_admin()
        return

    if affaire is None:
        render_landing()
        return

    st.title(affaire.nom)
    if not is_mode_presentation():
        if affaire.date_creation:
            st.caption(f"Slug : `{affaire.slug}`  ·  Créée le {affaire.date_creation[:10]}")
        else:
            st.caption(f"Slug : `{affaire.slug}`")

    render_status_line(affaire)

    client = get_llm_client()

    tab_overview, tab_dce, tab_analyse, tab_mt, tab_dpgf, tab_synthese, tab_pack = st.tabs(
        [
            "🏠 Vue d'ensemble",
            "📂 DCE",
            "🔍 Analyse",
            "📝 Mémoire technique",
            "💰 DPGF",
            "📊 Go / No-go",
            "📦 Candidature",
        ]
    )
    with tab_overview:
        render_tab_overview(affaire)
    with tab_dce:
        render_tab_dce(affaire)
    with tab_analyse:
        render_tab_analyse(affaire, client)
    with tab_mt:
        render_tab_mt(affaire, client)
    with tab_dpgf:
        render_tab_dpgf(affaire, client)
    with tab_synthese:
        render_tab_synthese(affaire, client)
    with tab_pack:
        render_tab_candidature(affaire, client)


# ---------------------------------------------------------------------------
# Entrée
# ---------------------------------------------------------------------------


affaire = render_sidebar()
render_main(affaire)
