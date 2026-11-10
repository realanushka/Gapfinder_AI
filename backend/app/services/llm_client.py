"""Thin wrapper around the LLM provider so every other service calls one place.

Two backends, chosen by `LLM_PROVIDER` in backend/.env:

* `anthropic` (default) -- Claude, with native JSON-schema structured outputs.
* `openai_compatible` -- any OpenAI-style endpoint: Google Gemini, Groq,
  OpenRouter, ... Several have free tiers. Set LLM_BASE_URL, LLM_API_KEY and
  LLM_MODEL. Those endpoints don't reliably honour `json_schema`, so the schema
  is put in the prompt and checked in code (`_check_against_schema`).

Retries are layered, deliberately separated:

* The SDKs retry transport-level failures (connection errors, 408/409/429,
  5xx) with their own backoff -- `max_retries` below makes that explicit.
* `retry_on_bad_response` handles what the SDKs cannot: a successful 200 whose
  body isn't usable JSON. Resampling genuinely fixes that.

Permanent failures (bad API key, malformed request, safety refusal, truncation)
are raised immediately. Retrying them would turn one clear error into a slow one.
"""

import json
import logging
from typing import Any

from anthropic import APIStatusError, AsyncAnthropic
from anthropic.types import Message
from openai import APIStatusError as OpenAIStatusError
from openai import AsyncOpenAI

from app.config import get_settings
from app.services.retry_policy import retry_on_bad_response

logger = logging.getLogger(__name__)
settings = get_settings()

# Generous ceilings because max_tokens caps thinking *and* visible output
# together on current models. A tight budget truncates the JSON mid-object,
# which surfaces as a parse error rather than an obvious "too small" failure.
JSON_MAX_TOKENS = 8192
TEXT_MAX_TOKENS = 2048

USE_OPENAI_COMPATIBLE = settings.llm_provider == "openai_compatible"

# LLM_MODEL may list several models, comma separated. Free tiers cap each model
# separately (e.g. 20 requests/day), so when one is exhausted, overloaded or
# retired we move to the next and remember it for later calls.
MODELS = [m.strip() for m in settings.llm_model.split(",") if m.strip()]
FALLBACK_STATUSES = {404, 429, 500, 503}
_model_cursor = 0

_client = (
    AsyncAnthropic(
        api_key=settings.anthropic_api_key,
        max_retries=3,
        timeout=120.0,  # seconds
    )
    if settings.anthropic_api_key and not USE_OPENAI_COMPATIBLE
    else None
)

# Gemini / Groq / OpenRouter / any OpenAI-style endpoint.
_compat_client = (
    AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        max_retries=3,
        timeout=120.0,  # seconds
    )
    if USE_OPENAI_COMPATIBLE and settings.llm_api_key and settings.llm_base_url
    else None
)


class LLMError(RuntimeError):
    """Base class for LLM failures the callers can report to the student."""


class LLMNotConfigured(LLMError):
    pass


class LLMRefused(LLMError):
    """The model declined the request; resampling will not help."""


class MalformedLLMResponse(LLMError):
    """The model returned a 200 whose body could not be used. Retryable."""


class LLMOutputTruncated(LLMError):
    """Output hit the token ceiling.

    Deliberately NOT a MalformedLLMResponse: the same prompt against the same
    ceiling truncates again, so retrying would triple the cost of an expensive
    call to reach the same failure.
    """


def _require_client() -> AsyncAnthropic:
    if _client is None:
        raise LLMNotConfigured(
            "ANTHROPIC_API_KEY is not configured — add it to backend/.env"
        )
    return _client


def _require_compat_client() -> AsyncOpenAI:
    if _compat_client is None:
        raise LLMNotConfigured(
            "LLM_PROVIDER=openai_compatible needs LLM_API_KEY and LLM_BASE_URL in backend/.env"
        )
    return _compat_client


def _extract_text(response: Message) -> str:
    """Concatenate the response's text blocks (Anthropic).

    Indexing `content[0]` is wrong: thinking is on by default on current models,
    so the first block is often a thinking block whose text is empty (the raw
    chain of thought is never returned). That silently yields "" and then a
    confusing JSON parse error.
    """
    if response.stop_reason == "refusal":
        raise LLMRefused("The model declined to answer this request.")

    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()

    if response.stop_reason == "max_tokens":
        raise LLMOutputTruncated(
            "The model's reply was cut off by the token limit. "
            "Shorten the source material or raise the token budget."
        )

    if not text:
        raise MalformedLLMResponse("The model returned no text content.")
    return text


def _strip_code_fences(text: str) -> str:
    """Unwrap ```json ... ``` fencing, which models add even when told not to."""
    if not text.startswith("```"):
        return text
    body = text.split("\n", 1)[1] if "\n" in text else ""
    if body.endswith("```"):
        body = body[: -len("```")]
    return body.strip()


async def _create_with_fallback(client: AsyncOpenAI, **request: Any):
    """Try each configured model in turn, starting from the last one that worked."""
    global _model_cursor
    last_error: OpenAIStatusError | None = None
    for offset in range(len(MODELS)):
        index = (_model_cursor + offset) % len(MODELS)
        try:
            response = await client.chat.completions.create(model=MODELS[index], **request)
        except OpenAIStatusError as err:
            if err.status_code not in FALLBACK_STATUSES:
                raise LLMError(f"LLM request failed ({err.status_code}): {err.message}") from err
            logger.warning("Model %s unavailable (%s); trying the next", MODELS[index], err.status_code)
            last_error = err
            continue
        _model_cursor = index
        return response
    assert last_error is not None
    raise LLMError(
        f"All configured models are unavailable (last error {last_error.status_code}). "
        "On a free tier this usually means today's request quota is used up -- "
        "try again later or add more models to LLM_MODEL."
    ) from last_error


async def _complete(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    json_mode: bool,
    schema: dict[str, Any] | None = None,
) -> str:
    """One LLM call on whichever backend is configured; returns the reply text."""
    if USE_OPENAI_COMPATIBLE:
        client = _require_compat_client()
        if json_mode and schema is not None:
            system_prompt += (
                "\n\nReply with ONLY a JSON object matching this JSON Schema:\n"
                + json.dumps(schema)
            )
        kwargs: dict[str, Any] = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = await _create_with_fallback(
            client,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            **kwargs,
        )

        if not response.choices:
            raise MalformedLLMResponse("The model returned no choices.")
        choice = response.choices[0]
        if choice.finish_reason == "content_filter":
            raise LLMRefused("The model declined to answer this request.")
        if choice.finish_reason == "length":
            raise LLMOutputTruncated(
                "The model's reply was cut off by the token limit. "
                "Shorten the source material or raise the token budget."
            )
        text = (choice.message.content or "").strip()
        if not text:
            raise MalformedLLMResponse("The model returned no text content.")
        return text

    client = _require_client()
    request: dict[str, Any] = {
        "model": settings.llm_model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    if json_mode and schema is not None:
        request["output_config"] = {"format": {"type": "json_schema", "schema": schema}}
    try:
        response = await client.messages.create(**request)
    except APIStatusError as err:
        # 4xx other than rate limiting is a request bug, not bad luck; the SDK
        # has already exhausted its own retries for anything transient.
        raise LLMError(f"LLM request failed ({err.status_code}): {err.message}") from err
    return _extract_text(response)


def _check_against_schema(value: Any, schema: dict[str, Any], path: str = "reply") -> None:
    """Check required keys, types and enums -- what native structured outputs enforce.

    Raises MalformedLLMResponse (retryable) so a bad sample is resampled.
    """
    options = schema.get("anyOf")
    if options:
        first_error: MalformedLLMResponse | None = None
        for option in options:
            try:
                _check_against_schema(value, option, path)
                return
            except MalformedLLMResponse as err:
                first_error = first_error or err
        raise first_error  # type: ignore[misc]

    kind = schema.get("type")
    if kind == "null":
        if value is not None:
            raise MalformedLLMResponse(f"{path} should be null")
    elif kind == "string":
        if not isinstance(value, str):
            raise MalformedLLMResponse(f"{path} should be a string")
        if "enum" in schema and value not in schema["enum"]:
            raise MalformedLLMResponse(f"{path} must be one of {schema['enum']}")
    elif kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise MalformedLLMResponse(f"{path} should be a number")
    elif kind == "array":
        if not isinstance(value, list):
            raise MalformedLLMResponse(f"{path} should be an array")
        for index, item in enumerate(value):
            _check_against_schema(item, schema["items"], f"{path}[{index}]")
    elif kind == "object":
        if not isinstance(value, dict):
            raise MalformedLLMResponse(f"{path} should be an object")
        for key in schema.get("required", []):
            if key not in value:
                raise MalformedLLMResponse(f"{path} is missing '{key}'")
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                _check_against_schema(value[key], sub, f"{path}.{key}")


@retry_on_bad_response(MalformedLLMResponse)
async def generate_json(
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call the LLM and parse its reply as strict JSON.

    Every generation step in the plan (topic extraction, quiz writing, grading
    narrative, gap-report reasons, plan task text, explain answers) goes through
    this function so JSON-parsing and retry/validation logic lives in one place.

    Pass `schema` (a JSON Schema object) to constrain the reply: Anthropic uses
    native structured outputs; OpenAI-compatible providers get the schema in the
    prompt and the reply is verified in code. Schemas live next to the prompts
    that need them, in `app/services/schemas.py`.
    """
    reply = await _complete(system_prompt, user_prompt, JSON_MAX_TOKENS, True, schema)
    payload = _strip_code_fences(reply)

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as err:
        logger.warning("LLM returned non-JSON (%s): %.200s", err.msg, payload)
        raise MalformedLLMResponse(f"Expected JSON, got: {payload[:200]}") from err

    if not isinstance(parsed, dict):
        raise MalformedLLMResponse(f"Expected a JSON object, got {type(parsed).__name__}")
    if schema is not None:
        _check_against_schema(parsed, schema)
    return parsed


@retry_on_bad_response(MalformedLLMResponse)
async def generate_text(system_prompt: str, user_prompt: str) -> str:
    return await _complete(system_prompt, user_prompt, TEXT_MAX_TOKENS, False)
