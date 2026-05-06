"""Suivi des coûts LLM cumulés sur la session Streamlit.

Tarifs Gemini 2.5 Flash (USD / 1M tokens, contexte ≤ 128k) :
  - Input texte/image  : 0.075
  - Input audio         : 0.30
  - Cached input texte  : 0.01875
  - Output (incl. thinking) : 0.30

On accumule les comptes dans st.session_state pour tracker visible côté UI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

# Tarifs USD par million de tokens (≤ 128k context)
PRIX_INPUT_PAR_M = 0.075
PRIX_INPUT_CACHED_PAR_M = 0.01875
PRIX_OUTPUT_PAR_M = 0.30  # inclut thinking


@dataclass
class UsageCumule:
    nb_appels: int = 0
    prompt_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    thoughts_tokens: int = 0

    @property
    def cout_input_usd(self) -> float:
        non_cached = max(self.prompt_tokens - self.cached_tokens, 0)
        return (
            non_cached * PRIX_INPUT_PAR_M / 1_000_000
            + self.cached_tokens * PRIX_INPUT_CACHED_PAR_M / 1_000_000
        )

    @property
    def cout_output_usd(self) -> float:
        # thoughts_tokens sont facturés comme output
        return (self.output_tokens + self.thoughts_tokens) * PRIX_OUTPUT_PAR_M / 1_000_000

    @property
    def cout_total_usd(self) -> float:
        return self.cout_input_usd + self.cout_output_usd

    def to_dict(self) -> dict:
        d = asdict(self)
        d["cout_input_usd"] = round(self.cout_input_usd, 6)
        d["cout_output_usd"] = round(self.cout_output_usd, 6)
        d["cout_total_usd"] = round(self.cout_total_usd, 6)
        return d


def _get_session_state():
    try:
        import streamlit as st

        return st.session_state
    except Exception:
        return None


def get_session_usage() -> UsageCumule:
    """Récupère le cumul de la session Streamlit, ou un nouveau tracker si hors Streamlit."""
    state = _get_session_state()
    if state is None:
        return UsageCumule()
    if "usage_cumule" not in state:
        state.usage_cumule = UsageCumule()
    return state.usage_cumule


def enregistrer_appel(
    prompt_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    thoughts_tokens: int = 0,
) -> None:
    """Enregistre un appel LLM dans le cumul de session."""
    u = get_session_usage()
    u.nb_appels += 1
    u.prompt_tokens += prompt_tokens or 0
    u.cached_tokens += cached_tokens or 0
    u.output_tokens += output_tokens or 0
    u.thoughts_tokens += thoughts_tokens or 0


def reset_session_usage() -> None:
    state = _get_session_state()
    if state is not None and "usage_cumule" in state:
        state.usage_cumule = UsageCumule()
