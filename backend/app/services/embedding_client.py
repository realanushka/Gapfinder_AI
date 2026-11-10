"""Wrapper around the embedding provider (Step 3 / Step 4 of the plan).

Like the LLM client, retries are split in two: the OpenAI SDK retries transport
failures itself (`max_retries` below makes that explicit), and
`retry_on_bad_response` covers the case the SDK cannot see -- a 200 whose
vectors are the wrong shape for the `chunks.embedding` column.
"""

import asyncio
import logging

from openai import APIStatusError, AsyncOpenAI

from app.config import get_settings
from app.services.retry_policy import retry_on_bad_response

logger = logging.getLogger(__name__)
settings = get_settings()

def _build_client() -> AsyncOpenAI | None:
    if settings.embedding_base_url:
        key = settings.embedding_api_key or settings.llm_api_key
        if not key:
            return None
        return AsyncOpenAI(
            api_key=key, base_url=settings.embedding_base_url, max_retries=3, timeout=60.0
        )
    if settings.openai_api_key:
        return AsyncOpenAI(api_key=settings.openai_api_key, max_retries=3, timeout=60.0)
    return None


_client = _build_client()


class EmbeddingError(RuntimeError):
    """Base class for embedding failures."""


class EmbeddingNotConfigured(EmbeddingError):
    pass


class EmbeddingRateLimited(EmbeddingError):
    """The provider's per-minute (or daily) limit was hit."""


class MalformedEmbeddingResponse(EmbeddingError):
    """Wrong vector count or width. Retryable."""


def _require_client() -> AsyncOpenAI:
    if _client is None:
        raise EmbeddingNotConfigured(
            "No embedding provider configured — set OPENAI_API_KEY, or EMBEDDING_BASE_URL + a key, in the root .env"
        )
    return _client


def _validate(vectors: list[list[float]], expected_count: int) -> list[list[float]]:
    """Check shape before these reach Postgres.

    A wrong width fails on insert with an opaque pgvector dimension error far
    from the cause, and a short list would silently mis-pair chunks with
    embeddings via zip().
    """
    if len(vectors) != expected_count:
        raise MalformedEmbeddingResponse(
            f"Expected {expected_count} embeddings, got {len(vectors)}"
        )

    for index, vector in enumerate(vectors):
        if len(vector) != settings.embedding_dim:
            raise MalformedEmbeddingResponse(
                f"Embedding {index} has width {len(vector)}, "
                f"but chunks.embedding is vector({settings.embedding_dim}). "
                "EMBEDDING_DIM must match the embedding model."
            )
    return vectors


# Providers cap how many texts one request may carry (Gemini: 100). A long
# textbook has hundreds of chunks and a big syllabus over a hundred topics, so
# requests are split rather than sent whole. 50 leaves headroom under the cap.
EMBED_BATCH_SIZE = 50
# Free tiers also limit requests per minute, which a long document will hit.
# Waiting lets the window reset; a daily limit simply fails after the last try.
RATE_LIMIT_WAIT_SECONDS = 25.0
RATE_LIMIT_ATTEMPTS = 4


@retry_on_bad_response(MalformedEmbeddingResponse)
async def _embed_batch(client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    """One request. Callers keep `texts` within EMBED_BATCH_SIZE."""
    try:
        extra = {"dimensions": settings.embedding_dim} if settings.embedding_base_url else {}
        response = await client.embeddings.create(
            model=settings.embedding_model, input=texts, **extra
        )
    except APIStatusError as err:
        if err.status_code == 429:
            raise EmbeddingRateLimited(
                f"Embedding rate limit reached ({err.status_code}): {err.message}"
            ) from err
        raise EmbeddingError(
            f"Embedding request failed ({err.status_code}): {err.message}"
        ) from err

    # The API may return items out of order; `index` is authoritative.
    # Some providers (Gemini) leave `index` as None on the first item; fall back to position.
    indexed = [
        (item.index if item.index is not None else position, item.embedding)
        for position, item in enumerate(response.data)
    ]
    ordered = [embedding for _, embedding in sorted(indexed, key=lambda pair: pair[0])]
    return _validate(ordered, len(texts))


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed any number of texts, preserving input order (callers zip on it)."""
    if not texts:
        return []

    client = _require_client()

    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start : start + EMBED_BATCH_SIZE]
        for attempt in range(1, RATE_LIMIT_ATTEMPTS + 1):
            try:
                vectors.extend(await _embed_batch(client, batch))
                break
            except EmbeddingRateLimited:
                if attempt == RATE_LIMIT_ATTEMPTS:
                    raise
                logger.warning(
                    "Embedding rate limit hit; waiting %.0fs (attempt %d/%d)",
                    RATE_LIMIT_WAIT_SECONDS,
                    attempt,
                    RATE_LIMIT_ATTEMPTS,
                )
                await asyncio.sleep(RATE_LIMIT_WAIT_SECONDS)
    return vectors


async def embed_text(text: str) -> list[float]:
    vectors = await embed_texts([text])
    return vectors[0]
