"""
ai_assistant/llm_client.py

Purpose: The only module that talks to an external LLM API
(OpenAI or Google Gemini). Reads credentials defensively via
`os.getenv` -- exactly the pattern `market_intelligence.email_notification`
already established for SMTP -- so the whole assistant works with zero
configuration, and upgrades to LLM-generated answers the moment a key
is added to `.env`. New variables (documented here, not written into
`.env.example` per the "don't modify previous files" rule):

    AI_ASSISTANT_PROVIDER=openai   # or "gemini" / "none"
    OPENAI_API_KEY=...
    OPENAI_MODEL=gpt-4o-mini
    GEMINI_API_KEY=...
    GEMINI_MODEL=gemini-1.5-flash
"""

import os

import requests

from logging_config import logger

AI_ASSISTANT_PROVIDER = os.getenv("AI_ASSISTANT_PROVIDER", "none").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

_REQUEST_TIMEOUT_SECONDS = 20


def is_llm_configured() -> bool:
    """Whether a usable LLM provider + key combination is configured."""
    if AI_ASSISTANT_PROVIDER == "openai":
        return bool(OPENAI_API_KEY)
    if AI_ASSISTANT_PROVIDER == "gemini":
        return bool(GEMINI_API_KEY)
    return False


def get_active_provider_label() -> str:
    """Human-readable label of the currently active provider, for UI display."""
    if not is_llm_configured():
        return "Local rule-based assistant (no LLM configured)"
    return f"{AI_ASSISTANT_PROVIDER.title()} ({OPENAI_MODEL if AI_ASSISTANT_PROVIDER == 'openai' else GEMINI_MODEL})"


def generate_llm_response(prompt: str) -> str | None:
    """
    Send a prompt to the configured LLM provider and return its text
    response, or None on any failure/misconfiguration -- callers
    (`ai_assistant.py`) always have `rule_based_responder.py` as a
    fallback, so a None here is never fatal.
    """
    if not is_llm_configured():
        return None

    try:
        if AI_ASSISTANT_PROVIDER == "openai":
            return _call_openai(prompt)
        if AI_ASSISTANT_PROVIDER == "gemini":
            return _call_gemini(prompt)
    except Exception as exc:  # noqa: BLE001 - any LLM failure must fall back gracefully, never crash the chat
        logger.error(f"LLM call failed ({AI_ASSISTANT_PROVIDER}): {exc}")
        return None

    return None


def _call_openai(prompt: str) -> str | None:
    """Call OpenAI's Chat Completions API."""
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": "You are FinSight AI's investment assistant. Be concise, factual, and never give definitive financial advice -- always frame suggestions as informational."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.4,
            "max_tokens": 500,
        },
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def _call_gemini(prompt: str) -> str | None:
    """Call Google Gemini's generateContent API."""
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        params={"key": GEMINI_API_KEY},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=_REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
