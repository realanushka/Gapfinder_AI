"""Shared retry policy for outbound AI calls.

Deliberately provider-agnostic: each client passes its own exception types, so
the embedding client never needs to know about Anthropic's error classes or
vice versa.

Note what this does *not* duplicate. Both the Anthropic and OpenAI SDKs already
retry connection errors, 408/409/429 and 5xx internally with exponential
backoff, so wrapping those again would only multiply the attempt count. The
clients set `max_retries` explicitly for that layer; this module exists for the
failures the SDKs cannot retry -- a 200 response whose *body* is unusable, such
as malformed JSON or a wrong-width embedding.
"""

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)

# Three attempts total. A bad-shape response is usually fixed by one resample;
# past that it is a prompt problem and more attempts just burn tokens.
MAX_ATTEMPTS = 3

T = TypeVar("T")


def retry_on_bad_response(
    *exception_types: type[BaseException],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Retry an async call when it raises one of `exception_types`.

    Only pass exceptions that a fresh attempt could plausibly fix. Never pass
    authentication or bad-request errors -- those fail identically every time,
    and retrying turns one clear error into a slow one.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt_number = 0
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(MAX_ATTEMPTS),
                wait=wait_exponential_jitter(initial=0.5, max=8.0),
                retry=retry_if_exception_type(exception_types),
                reraise=True,
            ):
                with attempt:
                    attempt_number += 1
                    if attempt_number > 1:
                        logger.warning(
                            "%s: retrying after unusable response (attempt %d/%d)",
                            func.__name__,
                            attempt_number,
                            MAX_ATTEMPTS,
                        )
                    return await func(*args, **kwargs)
            raise AssertionError("unreachable: AsyncRetrying always returns or raises")

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator
