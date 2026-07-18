"""LLM transport for Beerlight Runtime.

Thin wrapper over the validated slice provider.
Re-exports the slice transport — same model, same timeout, same retry.

Amendment 4: Live inference budget is hard-capped at 2 normal + 1×360 calls
through this transport. All other runs use fixtures, recorded responses, or
fake transport.
"""
from __future__ import annotations

# Re-export everything from the validated slice provider — this is the
# contract: Runtime uses the same transport, no new implementation.
from prism.slice.provider import (  # noqa: F401
    DEFAULT_MODEL,
    CALL_TIMEOUT,
    RETRY_DELAY,
    TransportError,
    call_llm,
    get_generator_model,
    get_judge_model,
)
