"""Gemini LLM wrapper with Google Search grounding."""

import os
import time

from google import genai
from google.genai import types
from google.genai import errors as genai_errors


def _get_secret(key: str) -> str | None:
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key)
    except Exception:
        return None


def _get_model() -> str:
    return _get_secret("LLM_MODEL") or "gemini-3.1-flash-lite"


_client = None
_client_key = None


def _get_client():
    global _client, _client_key
    api_key = _get_secret("GEMINI_API_KEY") or _get_secret("OPENAI_API_KEY")
    if not api_key:
        raise LLMError(
            "No API key found. Set GEMINI_API_KEY in .env (local) or "
            "Streamlit Cloud Secrets (Settings > Secrets)."
        )
    if _client is None or api_key != _client_key:
        _client = genai.Client(api_key=api_key)
        _client_key = api_key
    return _client


SYSTEM_BASE = "You are an AI study agent that helps students learn topics deeply."


class QuotaExceeded(Exception):
    pass


class LLMError(Exception):
    pass


def call(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    full_system = f"{SYSTEM_BASE}\n{system_prompt}"
    try:
        response = _get_client().models.generate_content(
            model=_get_model(),
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=full_system,
                temperature=temperature,
            ),
        )
        text = response.text
        if not text and response.candidates:
            text = response.candidates[0].content.parts[0].text
        return text or ""
    except genai_errors.ClientError as e:
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            raise QuotaExceeded(
                f"Gemini API quota exceeded (key starts with '{_client_key[:8] if _client_key else '?'}...'). "
                "Get a free AIzaSy key at https://aistudio.google.com/apikey"
            ) from e
        raise LLMError(f"Gemini API error: {err}") from e
    except Exception as e:
        raise LLMError(f"Unexpected error: {e}") from e
