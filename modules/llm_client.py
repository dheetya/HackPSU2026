"""Shared LLM client for OpenAI and xAI (Grok) with structured JSON output."""

from __future__ import annotations

import json
import os
import time
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

DEFAULT_MAX_RETRIES = 3
RETRY_BACKOFF_SEC = 2.0


def _provider_config() -> tuple[str, str, str]:
    """Return (base_url, api_key, model) from environment."""
    grok_key = os.environ.get("XAI_API_KEY") or os.environ.get("GROK_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    provider = (os.environ.get("SILOSIFTER_LLM_PROVIDER") or "").strip().lower()
    if not provider:
        provider = "grok" if grok_key else "openai"

    if provider in ("grok", "xai"):
        key = grok_key or openai_key
        if not key:
            raise RuntimeError(
                "Set XAI_API_KEY or GROK_API_KEY (or OPENAI_API_KEY) for LLM calls."
            )
        base = os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1")
        model = os.environ.get("SILOSIFTER_MODEL", "grok-2-latest")
        return base, key, model

    if not openai_key:
        raise RuntimeError("Set OPENAI_API_KEY for LLM calls.")
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("SILOSIFTER_MODEL", "gpt-4o-mini")
    return base, openai_key, model


def chat_json(
    system_prompt: str,
    user_prompt: str,
    schema_model: type[T],
    *,
    temperature: float = 0.0,
) -> T:
    """Call chat completions with JSON schema response and validate with Pydantic."""
    try:
        from openai import OpenAI, RateLimitError, APIConnectionError, APITimeoutError
    except ImportError as exc:
        raise RuntimeError("Install openai: pip install openai") from exc

    base_url, api_key, model = _provider_config()
    client = OpenAI(api_key=api_key, base_url=base_url, max_retries=0)

    schema = schema_model.model_json_schema()
    response_format: dict[str, Any] = {
        "type": "json_schema",
        "json_schema": {
            "name": schema_model.__name__,
            "schema": schema,
            "strict": True,
        },
    }

    last_error: Exception | None = None
    for attempt in range(DEFAULT_MAX_RETRIES):
        try:
            completion = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=response_format,
            )
            raw = completion.choices[0].message.content
            if not raw:
                raise ValueError("Empty LLM response")
            payload = json.loads(raw)
            return schema_model.model_validate(payload)
        except (RateLimitError, APIConnectionError, APITimeoutError) as exc:
            last_error = exc
            if attempt < DEFAULT_MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            raise
        except json.JSONDecodeError as exc:
            last_error = exc
            if attempt < DEFAULT_MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SEC)
                continue
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc
        except Exception as exc:
            last_error = exc
            if attempt < DEFAULT_MAX_RETRIES - 1 and "rate" in str(exc).lower():
                time.sleep(RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            raise

    raise RuntimeError(f"LLM call failed after retries: {last_error}")


def chat_json_raw(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    """Free-form JSON object response (for auditor output)."""
    try:
        from openai import OpenAI, RateLimitError, APIConnectionError, APITimeoutError
    except ImportError as exc:
        raise RuntimeError("Install openai: pip install openai") from exc

    base_url, api_key, model = _provider_config()
    client = OpenAI(api_key=api_key, base_url=base_url, max_retries=0)

    last_error: Exception | None = None
    for attempt in range(DEFAULT_MAX_RETRIES):
        try:
            completion = client.chat.completions.create(
                model=model,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            raw = completion.choices[0].message.content or "{}"
            return json.loads(raw)
        except (RateLimitError, APIConnectionError, APITimeoutError) as exc:
            last_error = exc
            if attempt < DEFAULT_MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SEC * (attempt + 1))
                continue
            raise
        except json.JSONDecodeError as exc:
            last_error = exc
            if attempt < DEFAULT_MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SEC)
                continue
            raise ValueError(f"Auditor returned invalid JSON: {exc}") from exc

    raise RuntimeError(f"Auditor LLM call failed: {last_error}")
