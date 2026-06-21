"""
Safe LLM invoke helper.

If rate-limit still happens after internal retries, return a fallback
response so the graph can continue instead of failing the whole task.
"""

import os
from types import SimpleNamespace
from typing import Any


def _is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    markers = [
        "429",
        "rate limit",
        "ratelimit",
        "too many requests",
        "tpm limit reached",
        "quota",
        "resource exhausted",
    ]
    return any(marker in text for marker in markers)


def invoke_with_rate_limit_fallback(
    llm: Any,
    prompt: Any,
    fallback_content: str,
    logger: Any,
    node_name: str,
):
    # Hard fallback mode for severe TPM pressure.
    # Enabled by default with TA_RATE_SAFE_MODE=1.
    force_fallback = os.getenv("TA_RATE_SAFE_MODE", "1").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if force_fallback:
        logger.warning(
            f"[{node_name}] TA_RATE_SAFE_MODE enabled, skip LLM call and use fallback."
        )
        return SimpleNamespace(content=fallback_content)

    try:
        return llm.invoke(prompt)
    except Exception as exc:
        if _is_rate_limit_error(exc):
            logger.warning(
                f"[{node_name}] LLM rate limit persists after retries, using fallback content."
            )
            return SimpleNamespace(content=fallback_content)
        raise

