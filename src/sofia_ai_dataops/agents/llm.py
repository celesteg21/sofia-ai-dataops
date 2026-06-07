"""Helpers compartidos para interaccion con LLMs y embeddings.

Centraliza la construccion de clientes, reintentos y politica de fallback
para que los nodos del grafo no dependan directamente de la API de OpenAI.
"""

from collections.abc import Callable
from typing import Any, TypeVar

import openai
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential

from sofia_ai_dataops.core.config import Settings

_F = TypeVar("_F", bound=Callable[..., Any])

_TRANSIENT_ERRORS = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.InternalServerError,
)


def make_llm_retry(max_retries: int = 3) -> Callable[[_F], _F]:
    """Devuelve un decorador de reintento configurable con jitter exponencial.

    Usa wait_random_exponential para evitar thundering herd cuando varios
    workers golpean el rate limit de OpenAI al mismo tiempo.
    """
    return retry(
        wait=wait_random_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(max_retries),
        retry=retry_if_exception_type(_TRANSIENT_ERRORS),
        reraise=True,
    )


# Decorador con defaults (3 reintentos).
# Los nodos deben usar make_llm_retry(settings.llm_max_retries) para respetar el valor de config.
llm_retry = make_llm_retry(max_retries=3)


def get_chat_client(settings: Settings) -> ChatOpenAI | None:
    """Devuelve un cliente ChatOpenAI si hay API key configurada, o None."""
    if not settings.openai_api_key:
        return None
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_retries=0,  # reintentos manejados por tenacity, no por langchain
    )


def get_embeddings_client(settings: Settings) -> OpenAIEmbeddings | None:
    """Devuelve un cliente OpenAIEmbeddings si hay API key configurada, o None."""
    if not settings.openai_api_key:
        return None
    return OpenAIEmbeddings(
        openai_api_key=settings.openai_api_key,
        model=settings.embedding_model,
    )
