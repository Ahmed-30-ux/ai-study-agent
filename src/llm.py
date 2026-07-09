"""Gemini LLM wrapper with Google Search grounding."""

import os
import time

from google import genai
from google.genai import types
from google.genai import errors as genai_errors


def _get_secret(key: str) -> str | None:
    if key == "GEMINI_API_KEY":
        try:
            import streamlit as st
            if st.session_state.get("api_key_input"):
                return st.session_state.api_key_input
        except Exception:
            pass
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key)
    except Exception:
        return None


def _get_model() -> str:
    return _get_secret("LLM_MODEL") or "gemini-2.0-flash"


_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = _get_secret("GEMINI_API_KEY") or _get_secret("OPENAI_API_KEY")
        if not api_key:
            raise LLMError(
                "No API key found. Set GEMINI_API_KEY in .env (local) or "
                "Streamlit Cloud Secrets (Settings > Secrets)."
            )
        _client = genai.Client(api_key=api_key)
    return _client


SYSTEM_BASE = "You are an AI study agent that helps students learn topics deeply."


class QuotaExceeded(Exception):
    pass


class LLMError(Exception):
    pass


def call(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    full_system = f"{SYSTEM_BASE}\n{system_prompt}"
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=full_system)]),
        types.Content(role="user", parts=[types.Part.from_text(text=user_prompt)]),
    ]
    try:
        response = _get_client().models.generate_content(
            model=_get_model(),
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=temperature,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        return response.text
    except genai_errors.ClientError as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            raise QuotaExceeded(
                "Gemini API quota exceeded. Try again later or use a different API key."
            ) from e
        raise LLMError(f"Gemini API error: {e}") from e
    except Exception as e:
        raise LLMError(f"Unexpected error: {e}") from e
