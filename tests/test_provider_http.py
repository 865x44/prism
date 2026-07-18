"""Tests for the http/opencode transport selection and the http call itself.

No real network: urllib.request.urlopen is monkeypatched.
"""
import json
import urllib.error

import pytest

from prism.slice import provider
from prism.slice.provider import TransportError


@pytest.fixture
def clean_env(monkeypatch):
    """Isolate transport/model env so tests are deterministic."""
    for var in (
        "PRISM_TRANSPORT",
        "PRISM_API_KEY",
        "OPENAI_API_KEY",
        "PRISM_BASE_URL",
        "PRISM_GENERATOR_MODEL",
        "PRISM_JUDGE_MODEL",
        "BEERLIGHT_SLICE_GENERATOR_MODEL",
        "BEERLIGHT_SLICE_JUDGE_MODEL",
    ):
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


# ---------- transport resolution ----------

def test_auto_transport_http_when_key_present(clean_env):
    clean_env.setenv("PRISM_API_KEY", "sk-test")
    assert provider._resolve_transport() == "http"


def test_auto_transport_opencode_without_key(clean_env):
    assert provider._resolve_transport() == "opencode"


def test_explicit_transport_overrides_key(clean_env):
    clean_env.setenv("PRISM_API_KEY", "sk-test")
    clean_env.setenv("PRISM_TRANSPORT", "opencode")
    assert provider._resolve_transport() == "opencode"


def test_unknown_transport_rejected(clean_env):
    clean_env.setenv("PRISM_TRANSPORT", "carrier-pigeon")
    with pytest.raises(TransportError):
        provider._resolve_transport()


def test_openai_api_key_fallback(clean_env):
    clean_env.setenv("OPENAI_API_KEY", "sk-fallback")
    assert provider._resolve_transport() == "http"


# ---------- model defaults ----------

def test_http_default_model(clean_env):
    clean_env.setenv("PRISM_API_KEY", "sk-test")
    assert provider.get_generator_model() == "gpt-4o-mini"
    assert provider.get_judge_model() == "gpt-4o-mini"


def test_opencode_default_model(clean_env):
    assert provider.get_generator_model() == "opencode-go/deepseek-v4-pro"


def test_model_env_override_and_legacy_fallback(clean_env):
    clean_env.setenv("PRISM_API_KEY", "sk-test")
    clean_env.setenv("BEERLIGHT_SLICE_GENERATOR_MODEL", "legacy-model")
    assert provider.get_generator_model() == "legacy-model"
    clean_env.setenv("PRISM_GENERATOR_MODEL", "new-model")
    assert provider.get_generator_model() == "new-model"


# ---------- http call ----------

class _FakeResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_http_call_success(clean_env):
    clean_env.setenv("PRISM_API_KEY", "sk-test")
    payload = {"choices": [{"message": {"content": "ответ модели"}}]}
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _FakeResponse(payload)

    clean_env.setattr(provider.urllib.request, "urlopen", fake_urlopen)
    result = provider._call_http("привет", "gpt-4o-mini")

    assert result == "ответ модели"
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-test"
    assert captured["body"]["model"] == "gpt-4o-mini"
    assert captured["body"]["messages"] == [
        {"role": "user", "content": "привет"}
    ]
    assert captured["timeout"] == provider.CALL_TIMEOUT


def test_http_call_respects_base_url(clean_env):
    clean_env.setenv("PRISM_API_KEY", "sk-test")
    clean_env.setenv("PRISM_BASE_URL", "https://openrouter.ai/api/v1/")
    captured = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        return _FakeResponse({"choices": [{"message": {"content": "ok"}}]})

    clean_env.setattr(provider.urllib.request, "urlopen", fake_urlopen)
    provider._call_http("p", "m")
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"


def test_http_call_http_error(clean_env):
    clean_env.setenv("PRISM_API_KEY", "sk-test")

    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url, 401, "Unauthorized", hdrs=None, fp=None
        )

    clean_env.setattr(provider.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(TransportError, match="401"):
        provider._call_http("p", "m")


def test_http_call_requires_key(clean_env):
    clean_env.setenv("PRISM_TRANSPORT", "http")
    with pytest.raises(TransportError, match="API_KEY"):
        provider._call_http("p", "m")


def test_http_call_bad_response_shape(clean_env):
    clean_env.setenv("PRISM_API_KEY", "sk-test")

    def fake_urlopen(request, timeout=None):
        return _FakeResponse({"unexpected": True})

    clean_env.setattr(provider.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(TransportError, match="unexpected response"):
        provider._call_http("p", "m")


# ---------- retry ----------

def test_call_llm_retries_once_then_succeeds(clean_env, monkeypatch):
    clean_env.setattr(provider.time, "sleep", lambda s: None)
    calls = []

    def flaky(prompt, model):
        calls.append(prompt)
        if len(calls) == 1:
            raise TransportError("boom")
        return "ok"

    monkeypatch.setattr(provider, "_call_once", flaky)
    assert provider.call_llm("p", "m") == "ok"
    assert len(calls) == 2


def test_call_llm_fails_after_two_attempts(clean_env, monkeypatch):
    clean_env.setattr(provider.time, "sleep", lambda s: None)
    monkeypatch.setattr(
        provider, "_call_once",
        lambda p, m: (_ for _ in ()).throw(TransportError("always")),
    )
    with pytest.raises(TransportError, match="2 attempts"):
        provider.call_llm("p", "m")
