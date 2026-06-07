"""Helpers compartidos para interaccion con LLMs y embeddings.

Centraliza la construccion de clientes, reintentos y politica de fallback
para que los nodos del grafo no dependan directamente de la API de OpenAI.
"""

import openai
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from sofia_ai_dataops.core.config import Settings

_TRANSIENT_ERRORS = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.InternalServerError,
)

llm_retry = retry(
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(_TRANSIENT_ERRORS),
    reraise=True,
)


def get_chat_client(settings: Settings) -> ChatOpenAI | None:
    """Devuelve un cliente ChatOpenAI si hay API key configurada, o None."""
    if not settings.openai_api_key:
        return None
    return ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_retries=0,
    )


def get_embeddings_client(settings: Settings) -> OpenAIEmbeddings | None:
    """Devuelve un cliente OpenAIEmbeddings si hay API key configurada, o None."""
    if not settings.openai_api_key:
        return None
    return OpenAIEmbeddings(
        openai_api_key=settings.openai_api_key,
        model=settings.embedding_model,
    )
