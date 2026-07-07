"""
Thin wrapper around the OpenAI client (CONVENTIONS.md "Models & embeddings"):
every model call in the codebase goes through here so a model swap is one
line and prompt/language handling stays consistent.

Raises LLMError for ANY failure (missing package, missing key, API error,
empty completion) so callers have exactly one exception to catch and can
fall back deterministically — a node must never crash the graph because a
model call failed.
"""
from __future__ import annotations

import os


class LLMError(RuntimeError):
    """Any failure to obtain a completion — callers catch this and fall back."""


def complete(
    prompt: str,
    *,
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 300,
) -> str:
    """Returns the completion text for a single-turn prompt.

    `model` defaults to the OPENAI_MODEL_MINI env var (GPT-5.4 Mini) — the
    workhorse tier for the forensic and oracle nodes (architecture.md §1).
    """
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMError("openai package is not installed") from exc

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMError("OPENAI_API_KEY is not set")

    resolved_model = model or os.environ.get("OPENAI_MODEL_MINI", "gpt-5.4-mini")
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        response = OpenAI(api_key=api_key).chat.completions.create(
            model=resolved_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
    except Exception as exc:
        raise LLMError(f"completion failed: {exc}") from exc

    if not content or not content.strip():
        raise LLMError("model returned an empty completion")
    return content.strip()


__all__ = ["LLMError", "complete"]
