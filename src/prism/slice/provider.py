"""LLM transport for Prism.

Two transports:

- ``http`` — OpenAI-compatible Chat Completions endpoint (stdlib urllib).
  Works with OpenAI, OpenRouter, and any compatible gateway.
- ``opencode`` — subprocess to the ``opencode`` CLI (fallback, used when
  no API key is configured).

Config via env:
  PRISM_TRANSPORT                auto | http | opencode  (default: auto —
                                 http when an API key is set, else opencode)
  PRISM_API_KEY                  API key for the http transport
                                 (fallback: OPENAI_API_KEY)
  PRISM_BASE_URL                 default: https://api.openai.com/v1
  PRISM_GENERATOR_MODEL          generator model (fallback:
                                 BEERLIGHT_SLICE_GENERATOR_MODEL)
  PRISM_JUDGE_MODEL              judge model (fallback:
                                 BEERLIGHT_SLICE_JUDGE_MODEL)

Model defaults depend on the resolved transport:
  http     → gpt-4o-mini
  opencode → opencode-go/deepseek-v4-pro
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request

DEFAULT_MODEL = "opencode-go/deepseek-v4-pro"
DEFAULT_HTTP_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
CALL_TIMEOUT = 600  # seconds
RETRY_DELAY = 10  # seconds

TRANSPORT_AUTO = "auto"
TRANSPORT_HTTP = "http"
TRANSPORT_OPENCODE = "opencode"


class TransportError(Exception):
    """Raised when the LLM transport fails (non-200, timeout, etc.)."""


def _get_api_key() -> str | None:
    return os.environ.get("PRISM_API_KEY") or os.environ.get("OPENAI_API_KEY")


def _resolve_transport() -> str:
    """Resolve which transport to use: explicit env or auto-detection."""
    explicit = os.environ.get("PRISM_TRANSPORT", "").strip().lower()
    if explicit in (TRANSPORT_HTTP, TRANSPORT_OPENCODE):
        return explicit
    if explicit and explicit != TRANSPORT_AUTO:
        raise TransportError(
            f"Unknown PRISM_TRANSPORT={explicit!r} "
            f"(expected auto|http|opencode)"
        )
    return TRANSPORT_HTTP if _get_api_key() else TRANSPORT_OPENCODE


def _default_model() -> str:
    if _resolve_transport() == TRANSPORT_HTTP:
        return DEFAULT_HTTP_MODEL
    return DEFAULT_MODEL


def get_generator_model() -> str:
    return (
        os.environ.get("PRISM_GENERATOR_MODEL")
        or os.environ.get("BEERLIGHT_SLICE_GENERATOR_MODEL")
        or _default_model()
    )


def get_judge_model() -> str:
    return (
        os.environ.get("PRISM_JUDGE_MODEL")
        or os.environ.get("BEERLIGHT_SLICE_JUDGE_MODEL")
        or _default_model()
    )


def _call_opencode(prompt: str, model: str) -> str:
    """Single call to opencode CLI. Returns stdout on success."""
    try:
        result = subprocess.run(
            ["opencode", "run", "--model", model, prompt],
            capture_output=True,
            text=True,
            timeout=CALL_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        raise TransportError(f"opencode call timed out after {CALL_TIMEOUT}s")
    except FileNotFoundError:
        raise TransportError(
            "opencode CLI not found. Is it installed and on PATH?"
        )

    if result.returncode != 0:
        raise TransportError(
            f"opencode exited with code {result.returncode}: "
            f"{result.stderr.strip()}"
        )

    return result.stdout


def _call_http(prompt: str, model: str) -> str:
    """Single call to an OpenAI-compatible Chat Completions endpoint."""
    api_key = _get_api_key()
    if not api_key:
        raise TransportError(
            "PRISM_API_KEY (or OPENAI_API_KEY) is required for the http "
            "transport"
        )
    base_url = os.environ.get("PRISM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    url = f"{base_url}/chat/completions"

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=CALL_TIMEOUT) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        snippet = ""
        try:
            snippet = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        raise TransportError(f"http {e.code} from {url}: {snippet}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise TransportError(f"http call to {url} failed: {e}")

    try:
        data = json.loads(body)
        return data["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
        raise TransportError(
            f"unexpected response shape from {url}: {e}: {body[:500]}"
        )


def _call_once(prompt: str, model: str) -> str:
    if _resolve_transport() == TRANSPORT_HTTP:
        return _call_http(prompt, model)
    return _call_opencode(prompt, model)


def call_llm(prompt: str, model: str) -> str:
    """Call the LLM with one retry on transport error.

    Args:
        prompt: The full prompt text to send.
        model: Model identifier (e.g. 'gpt-4o-mini').

    Returns:
        The model's text response.

    Raises:
        TransportError: After two failed attempts (original + 1 retry).
    """
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            return _call_once(prompt, model)
        except TransportError as e:
            last_error = e
            if attempt == 0:
                time.sleep(RETRY_DELAY)
            continue

    raise TransportError(
        f"LLM call failed after 2 attempts: {last_error}"
    )
