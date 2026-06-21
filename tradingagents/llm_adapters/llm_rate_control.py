"""
LLM call rate control and unified 429 retry.

Goals:
- Control request throughput (TPM/RPM) for each provider+model key.
- Add exponential backoff retry for rate-limit errors.
- Keep integration low-risk by wrapping existing llm.invoke/ainvoke methods.
"""

from __future__ import annotations

import os
import time
import random
import threading
from collections import deque
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from typing import Any, Deque, Dict, Optional, Tuple

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except Exception:
        return default


def _get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        return str(value)
    except Exception:
        return ""


def _estimate_tokens_from_text(text: str) -> int:
    # Conservative approximation for mixed CN/EN content.
    return max(1, len(text) // 2)


def _estimate_tokens_from_payload(payload: Any) -> int:
    if payload is None:
        return 1
    if isinstance(payload, str):
        return _estimate_tokens_from_text(payload)
    if isinstance(payload, (int, float, bool)):
        return _estimate_tokens_from_text(str(payload))
    if isinstance(payload, dict):
        return sum(_estimate_tokens_from_payload(v) for v in payload.values()) + 1
    if isinstance(payload, (list, tuple, set)):
        return sum(_estimate_tokens_from_payload(v) for v in payload) + 1
    content = getattr(payload, "content", None)
    if content is not None:
        return _estimate_tokens_from_payload(content)
    return _estimate_tokens_from_text(_safe_str(payload))


def _extract_retry_after_seconds(exc: Exception) -> Optional[float]:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) if response is not None else None
    if not headers:
        return None
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if not raw:
        return None
    raw = raw.strip()
    try:
        return max(0.0, float(raw))
    except Exception:
        pass
    try:
        dt = parsedate_to_datetime(raw)
        return max(0.0, dt.timestamp() - time.time())
    except Exception:
        return None


def _is_rate_limit_error(exc: Exception) -> bool:
    text = _safe_str(exc).lower()
    markers = [
        "429",
        "rate limit",
        "ratelimit",
        "too many requests",
        "tpm limit reached",
        "quota",
        "resource exhausted",
    ]
    if any(m in text for m in markers):
        return True
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    response = getattr(exc, "response", None)
    if response is not None and getattr(response, "status_code", None) == 429:
        return True
    return False


@dataclass
class _LimiterState:
    token_events: Deque[Tuple[float, int]] = field(default_factory=deque)
    call_events: Deque[float] = field(default_factory=deque)
    lock: threading.Lock = field(default_factory=threading.Lock)


_GLOBAL_STATES: Dict[str, _LimiterState] = {}
_GLOBAL_STATES_LOCK = threading.Lock()


def _get_state(key: str) -> _LimiterState:
    with _GLOBAL_STATES_LOCK:
        state = _GLOBAL_STATES.get(key)
        if state is None:
            state = _LimiterState()
            _GLOBAL_STATES[key] = state
        return state


def _purge_expired(state: _LimiterState, now: float, window_seconds: float) -> None:
    token_cutoff = now - window_seconds
    while state.token_events and state.token_events[0][0] <= token_cutoff:
        state.token_events.popleft()
    while state.call_events and state.call_events[0] <= token_cutoff:
        state.call_events.popleft()


def _token_wait_seconds(
    events: Deque[Tuple[float, int]],
    now: float,
    window_seconds: float,
    max_tpm: int,
    needed_tokens: int,
) -> float:
    if max_tpm <= 0:
        return 0.0
    used = sum(tok for _, tok in events)
    if used + needed_tokens <= max_tpm:
        return 0.0
    remaining = used
    for ts, tok in events:
        remaining -= tok
        if remaining + needed_tokens <= max_tpm:
            return max(0.0, ts + window_seconds - now) + 0.01
    return window_seconds


def _call_wait_seconds(
    events: Deque[float],
    now: float,
    window_seconds: float,
    max_rpm: int,
) -> float:
    if max_rpm <= 0:
        return 0.0
    if len(events) < max_rpm:
        return 0.0
    oldest = events[0]
    return max(0.0, oldest + window_seconds - now) + 0.01


def _acquire_budget(
    limiter_key: str,
    max_tpm: int,
    max_rpm: int,
    estimated_tokens: int,
    window_seconds: float,
) -> None:
    state = _get_state(limiter_key)
    while True:
        with state.lock:
            now = time.time()
            _purge_expired(state, now, window_seconds)
            wait_tokens = _token_wait_seconds(
                state.token_events, now, window_seconds, max_tpm, estimated_tokens
            )
            wait_calls = _call_wait_seconds(
                state.call_events, now, window_seconds, max_rpm
            )
            wait_time = max(wait_tokens, wait_calls)
            if wait_time <= 0:
                state.token_events.append((now, estimated_tokens))
                state.call_events.append(now)
                return
        time.sleep(min(wait_time, 5.0))


def _role_default_tpm(role: str) -> int:
    if role == "deep":
        return _get_int_env("TA_LLM_DEEP_MAX_TPM", 12000)
    return _get_int_env("TA_LLM_QUICK_MAX_TPM", 20000)


def _role_default_rpm(role: str) -> int:
    if role == "deep":
        return _get_int_env("TA_LLM_DEEP_MAX_RPM", 6)
    return _get_int_env("TA_LLM_QUICK_MAX_RPM", 12)


def _build_limiter_key(provider: str, model: str, role: str) -> str:
    provider_key = (provider or "unknown").strip().lower()
    model_key = (model or "unknown").strip().lower()
    return f"{provider_key}:{model_key}:{role}"


def attach_rate_control_to_llm(
    llm: Any,
    provider: str,
    model: str,
    role: str,
    retry_times: int = 3,
    max_tpm: Optional[int] = None,
    max_rpm: Optional[int] = None,
) -> Any:
    """
    Patch an llm instance with:
    - budget-aware invoke/ainvoke
    - unified 429 retry
    - recursive guard for bind_tools / with_structured_output
    """
    if llm is None:
        return llm

    if getattr(llm, "_ta_rate_control_attached", False):
        return llm

    if not _get_bool_env("TA_LLM_RATE_CONTROL_ENABLED", True):
        setattr(llm, "_ta_rate_control_attached", True)
        return llm

    window_seconds = float(_get_int_env("TA_LLM_RATE_WINDOW_SECONDS", 60))
    limiter_key = _build_limiter_key(provider, model, role)
    effective_tpm = int(max_tpm or _role_default_tpm(role))
    effective_rpm = int(max_rpm or _role_default_rpm(role))
    effective_retry = max(1, int(retry_times))
    retry_base = _get_float_env("TA_LLM_RETRY_BASE_SECONDS", 2.0)
    retry_cap = _get_float_env("TA_LLM_RETRY_MAX_SECONDS", 45.0)
    retry_jitter = _get_float_env("TA_LLM_RETRY_JITTER_SECONDS", 1.0)

    original_invoke = getattr(llm, "invoke", None)
    original_ainvoke = getattr(llm, "ainvoke", None)
    original_bind_tools = getattr(llm, "bind_tools", None)
    original_structured = getattr(llm, "with_structured_output", None)

    if callable(original_invoke):
        def guarded_invoke(*args, **kwargs):
            payload = args[0] if args else kwargs.get("input")
            input_tokens = _estimate_tokens_from_payload(payload)
            max_output_tokens = (
                kwargs.get("max_tokens")
                or getattr(llm, "max_tokens", None)
                or 1200
            )
            estimated_total = int(input_tokens + max(200, int(max_output_tokens)))
            _acquire_budget(
                limiter_key=limiter_key,
                max_tpm=effective_tpm,
                max_rpm=effective_rpm,
                estimated_tokens=estimated_total,
                window_seconds=window_seconds,
            )

            for attempt in range(1, effective_retry + 1):
                try:
                    return original_invoke(*args, **kwargs)
                except Exception as exc:
                    if not _is_rate_limit_error(exc):
                        raise
                    if attempt >= effective_retry:
                        # 429 重试耗尽：若启用 fallback 则返回占位内容，避免任务卡死
                        if _get_bool_env("TA_LLM_429_FALLBACK_ENABLED", True):
                            logger.warning(
                                f"[LLMRateControl] 429 重试耗尽，使用 fallback 继续: {_safe_str(exc)[:200]}"
                            )
                            try:
                                from langchain_core.messages import AIMessage
                                return AIMessage(content="[因API限流，本步骤分析暂略，建议稍后重试]")
                            except ImportError:
                                raise
                        raise
                    retry_after = _extract_retry_after_seconds(exc)
                    backoff = min(retry_cap, retry_base * (2 ** (attempt - 1)))
                    sleep_seconds = retry_after if retry_after is not None else backoff
                    sleep_seconds = max(
                        0.5, sleep_seconds + random.uniform(0, retry_jitter)
                    )
                    logger.warning(
                        f"[LLMRateControl] 429 retry {attempt}/{effective_retry} "
                        f"key={limiter_key}, wait={sleep_seconds:.2f}s"
                    )
                    time.sleep(sleep_seconds)

        object.__setattr__(llm, "invoke", guarded_invoke)

    if callable(original_ainvoke):
        async def guarded_ainvoke(*args, **kwargs):
            payload = args[0] if args else kwargs.get("input")
            input_tokens = _estimate_tokens_from_payload(payload)
            max_output_tokens = (
                kwargs.get("max_tokens")
                or getattr(llm, "max_tokens", None)
                or 1200
            )
            estimated_total = int(input_tokens + max(200, int(max_output_tokens)))
            _acquire_budget(
                limiter_key=limiter_key,
                max_tpm=effective_tpm,
                max_rpm=effective_rpm,
                estimated_tokens=estimated_total,
                window_seconds=window_seconds,
            )

            for attempt in range(1, effective_retry + 1):
                try:
                    return await original_ainvoke(*args, **kwargs)
                except Exception as exc:
                    if not _is_rate_limit_error(exc):
                        raise
                    if attempt >= effective_retry:
                        if _get_bool_env("TA_LLM_429_FALLBACK_ENABLED", True):
                            logger.warning(
                                f"[LLMRateControl] async 429 重试耗尽，使用 fallback: {_safe_str(exc)[:200]}"
                            )
                            try:
                                from langchain_core.messages import AIMessage
                                return AIMessage(content="[因API限流，本步骤分析暂略，建议稍后重试]")
                            except ImportError:
                                raise
                        raise
                    retry_after = _extract_retry_after_seconds(exc)
                    backoff = min(retry_cap, retry_base * (2 ** (attempt - 1)))
                    sleep_seconds = retry_after if retry_after is not None else backoff
                    sleep_seconds = max(
                        0.5, sleep_seconds + random.uniform(0, retry_jitter)
                    )
                    logger.warning(
                        f"[LLMRateControl] async 429 retry {attempt}/{effective_retry} "
                        f"key={limiter_key}, wait={sleep_seconds:.2f}s"
                    )
                    import asyncio
                    await asyncio.sleep(sleep_seconds)

        object.__setattr__(llm, "ainvoke", guarded_ainvoke)

    if callable(original_bind_tools):
        def guarded_bind_tools(*args, **kwargs):
            bound = original_bind_tools(*args, **kwargs)
            return attach_rate_control_to_llm(
                bound,
                provider=provider,
                model=model,
                role=role,
                retry_times=effective_retry,
                max_tpm=effective_tpm,
                max_rpm=effective_rpm,
            )

        object.__setattr__(llm, "bind_tools", guarded_bind_tools)

    if callable(original_structured):
        def guarded_with_structured_output(*args, **kwargs):
            structured = original_structured(*args, **kwargs)
            return attach_rate_control_to_llm(
                structured,
                provider=provider,
                model=model,
                role=role,
                retry_times=effective_retry,
                max_tpm=effective_tpm,
                max_rpm=effective_rpm,
            )

        object.__setattr__(llm, "with_structured_output", guarded_with_structured_output)

    setattr(llm, "_ta_rate_control_attached", True)
    logger.info(
        f"[LLMRateControl] attached key={limiter_key} tpm={effective_tpm} "
        f"rpm={effective_rpm} retry={effective_retry}"
    )
    return llm

