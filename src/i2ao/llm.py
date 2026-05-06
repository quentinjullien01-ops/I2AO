"""Wrapper Google Gemini avec sortie structurée pydantic.

Le DCE est volumineux (50-200 pages) et stable : on le requête plusieurs fois pour
extraction puis rédaction. Pour la version actuelle on passe le DCE dans le message
utilisateur ; le context caching explicite (caches.create) sera ajouté si la
consommation l'exige (rentable au-delà de ~32k tokens cumulés).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Callable, Type, TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError

from .config import GOOGLE_API_KEY, LLM_MAX_TOKENS, LLM_MODEL

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


class LLMOverloadError(LLMError):
    """Gemini est sature (5xx ou 429) au-dela des tentatives de retry.

    L'appelant peut afficher un message convivial et proposer de relancer.
    """


_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
_RETRY_MAX_ATTEMPTS = 8
_RETRY_BASE_DELAY = 2.0  # secondes
_RETRY_MAX_DELAY = 60.0  # plafond pour eviter d'attendre 256s+ sur la 8e tentative


def _with_retry(fn: Callable[[], object]) -> object:
    """Retry exponentiel sur 429/5xx (Gemini sujet a des pics de saturation).

    Levee LLMOverloadError si toutes les tentatives echouent — ce qui permet
    a l'UI Streamlit de l'attraper et d'afficher un message lisible plutot
    qu'une stack trace.
    """
    last_exc: Exception | None = None
    for attempt in range(_RETRY_MAX_ATTEMPTS):
        try:
            return fn()
        except genai_errors.APIError as e:
            status = getattr(e, "code", None) or getattr(e, "status_code", None)
            if status not in _RETRY_STATUS_CODES:
                raise
            last_exc = e
            delay = min(_RETRY_BASE_DELAY * (2**attempt), _RETRY_MAX_DELAY)
            logger.warning(
                "Gemini %s sur tentative %d/%d, retry dans %.1fs",
                status,
                attempt + 1,
                _RETRY_MAX_ATTEMPTS,
                delay,
            )
            time.sleep(delay)
    raise LLMOverloadError(
        f"Gemini est sature : {_RETRY_MAX_ATTEMPTS} tentatives ont retourne une erreur "
        f"transitoire (5xx/429). Reessaye dans quelques minutes."
    ) from last_exc


@dataclass
class LLMUsage:
    prompt_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    thoughts_tokens: int = 0

    @property
    def cache_hit_ratio(self) -> float:
        total = self.prompt_tokens + self.cached_tokens
        if total == 0:
            return 0.0
        return self.cached_tokens / total


class LLMClient:
    def __init__(self, api_key: str = GOOGLE_API_KEY, model: str = LLM_MODEL) -> None:
        if not api_key:
            raise LLMError(
                "GOOGLE_API_KEY manquante. La coller dans .env à la racine du projet "
                "(https://aistudio.google.com/apikey)."
            )
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.last_usage: LLMUsage | None = None

    def call(
        self,
        system_prompt: str,
        dce_context: str | None,
        user_message: str,
        max_tokens: int = LLM_MAX_TOKENS,
        temperature: float = 0.4,
        thinking_budget: int | None = 0,
    ) -> str:
        """Appel texte standard.

        thinking_budget : nombre de tokens alloués au raisonnement interne du modèle.
        - 0 (défaut) : désactivé. Pertinent pour génération de texte (rédaction MT).
        - 512-2048 : pour analyses qui bénéficient de raisonnement.
        - None : laisse le modèle décider (peut consommer beaucoup de tokens).
        """
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=temperature,
            thinking_config=_thinking_config(thinking_budget),
        )
        contents = self._build_contents(dce_context, user_message)
        response = _with_retry(
            lambda: self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
        )
        self._record_usage(response)
        return response.text or ""

    def extract_structured(
        self,
        system_prompt: str,
        dce_context: str | None,
        user_message: str,
        schema: Type[T],
        max_tokens: int = LLM_MAX_TOKENS,
        temperature: float = 0.2,
        thinking_budget: int | None = 1024,
    ) -> T:
        """Appel avec sortie JSON validée par un schéma pydantic.

        Utilise le mode response_schema natif de Gemini : le SDK retourne directement
        un objet pydantic dans response.parsed quand le schéma est fourni.

        thinking_budget par défaut 1024 : l'extraction structurée bénéficie du
        raisonnement (déduplication, classification, importance).
        """
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema,
            thinking_config=_thinking_config(thinking_budget),
        )
        contents = self._build_contents(dce_context, user_message)
        response = _with_retry(
            lambda: self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
        )
        self._record_usage(response)

        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, schema):
            return parsed
        if isinstance(parsed, dict):
            try:
                return schema.model_validate(parsed)
            except ValidationError as e:
                raise LLMError(
                    f"Réponse parsed invalide pour {schema.__name__} : {e}"
                ) from e

        raw = response.text or ""
        try:
            data = json.loads(raw)
            return schema.model_validate(data)
        except (ValidationError, json.JSONDecodeError) as e:
            raise LLMError(
                f"Réponse JSON invalide pour {schema.__name__} : {e}\nBrut : {raw[:500]}"
            ) from e

    def _build_contents(self, dce_context: str | None, user_message: str) -> str:
        if dce_context:
            return f"<dce>\n{dce_context}\n</dce>\n\n{user_message}"
        return user_message

    def _record_usage(self, response: object) -> None:
        u = getattr(response, "usage_metadata", None)
        if u is None:
            return
        prompt = getattr(u, "prompt_token_count", 0) or 0
        output = getattr(u, "candidates_token_count", 0) or 0
        cached = getattr(u, "cached_content_token_count", 0) or 0
        thoughts = getattr(u, "thoughts_token_count", 0) or 0
        self.last_usage = LLMUsage(
            prompt_tokens=prompt,
            output_tokens=output,
            cached_tokens=cached,
            thoughts_tokens=thoughts,
        )
        # Cumul session (ne casse rien si hors contexte Streamlit)
        try:
            from .usage_tracker import enregistrer_appel

            enregistrer_appel(
                prompt_tokens=prompt,
                output_tokens=output,
                cached_tokens=cached,
                thoughts_tokens=thoughts,
            )
        except Exception:
            pass
        logger.debug("LLM usage: %s", self.last_usage)


def _thinking_config(budget: int | None) -> types.ThinkingConfig | None:
    """Construit un ThinkingConfig. None = laisse le modèle décider (défaut SDK).

    Sur Gemini 2.5 Pro, le thinking est ON par défaut et peut consommer la
    totalité de max_output_tokens. On le désactive (budget=0) ou on le borne.
    """
    if budget is None:
        return None
    return types.ThinkingConfig(thinking_budget=budget)


def truncate_for_context(text: str, max_chars: int = 1_500_000) -> str:
    """Garde-fou : tronque un DCE trop volumineux avant envoi.

    Gemini 2.5 Pro accepte 1M tokens en entrée (~4M chars). On reste prudent.
    """
    if len(text) <= max_chars:
        return text
    head = text[: max_chars // 2]
    tail = text[-max_chars // 2 :]
    return f"{head}\n\n[... DOCUMENT TRONQUÉ POUR TENIR DANS LE CONTEXTE ...]\n\n{tail}"
