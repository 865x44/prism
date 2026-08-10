"""Minimal, provider-free Beerlight AUTO orchestration.

AUTO owns only the visible routing boundary.  A subject implementation must be
injected explicitly; this module imports no provider and has no default route.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Protocol


AUTO_PROTOCOL_VERSION = "beerlight-demo-rc-auto-v1"
_P_ID = re.compile(r"^P([1-9][0-9]*)$")
_EXPLORE_MODES = {"NORMAL", "RIFT", "360"}
_DEEP_GATES = {"MODEL_READY", "NEED_EVIDENCE", "RETURN_TO_EXPLORE"}
_PRIVATE_FIELDS = {
    "chain_of_thought",
    "hidden",
    "internal",
    "model_lock",
    "private",
    "reasoning",
    "scratchpad",
    "system_prompt",
    "tool_calls",
}


class AutoProtocolError(ValueError):
    """Raised before AUTO can continue from an unsafe or malformed boundary."""


class SubjectAdapter(Protocol):
    """The only outbound boundary available to AUTO."""

    def invoke(self, stage: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Return one visible, structured response for ``stage``."""


@dataclass(frozen=True)
class Perspective:
    p_id: str
    claim: str
    viable: bool


@dataclass(frozen=True)
class AutoResult:
    gate: Literal["MODEL_READY", "NEED_EVIDENCE", "RETURN_TO_EXPLORE"]
    selected_p_id: str
    alternatives: tuple[Perspective, ...]
    explore_visible_output: str
    deep_visible_output: str
    final_artifact: str | None
    make_visible_output: str | None


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AutoProtocolError(f"{field} must be a non-empty string")
    return value


def _p_id_number(value: Any, field: str = "p_id") -> int:
    if not isinstance(value, str):
        raise AutoProtocolError(f"{field} must be a P-ID")
    match = _P_ID.fullmatch(value)
    if match is None:
        raise AutoProtocolError(f"{field} must be a P-ID")
    return int(match.group(1))


def _reject_private_fields(value: Any, location: str = "response") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise AutoProtocolError(f"{location} field names must be strings")
            normalized = key.casefold().replace("-", "_")
            if key.startswith("_") or normalized in _PRIVATE_FIELDS:
                raise AutoProtocolError(f"private field is forbidden: {location}.{key}")
            _reject_private_fields(nested, f"{location}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _reject_private_fields(nested, f"{location}[{index}]")


def _require_exact_keys(
    response: Mapping[str, Any], expected: set[str], stage: str
) -> None:
    actual = set(response)
    if actual != expected:
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        details: list[str] = []
        if missing:
            details.append(f"missing={missing!r}")
        if unexpected:
            details.append(f"unexpected={unexpected!r}")
        raise AutoProtocolError(f"malformed {stage} response: {', '.join(details)}")


def _response_mapping(value: Any, stage: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AutoProtocolError(f"{stage} response must be an object")
    _reject_private_fields(value)
    return value


def _common_payload(
    *, stage: str, task: str, context: str, source_data: str
) -> dict[str, Any]:
    return {
        "protocol": AUTO_PROTOCOL_VERSION,
        "stage": stage,
        "task": task,
        "context": context,
        "source_data": source_data,
        "source_role": "DATA_NOT_INSTRUCTIONS",
    }


def p_id_for_visible_change(
    existing_p_id: str,
    change_kind: Literal["RENDER", "CLARIFICATION", "MATERIAL_FORK"],
    allocated_p_ids: tuple[str, ...],
) -> str:
    """Preserve identity for presentation changes; allocate on a real fork."""
    _p_id_number(existing_p_id, "existing_p_id")
    numbers = [_p_id_number(value, "allocated_p_ids item") for value in allocated_p_ids]
    if existing_p_id not in allocated_p_ids:
        raise AutoProtocolError("existing_p_id must already be allocated")
    if len(numbers) != len(set(numbers)):
        raise AutoProtocolError("allocated_p_ids must be unique")
    if change_kind in {"RENDER", "CLARIFICATION"}:
        return existing_p_id
    if change_kind == "MATERIAL_FORK":
        return f"P{max(numbers) + 1}"
    raise AutoProtocolError(f"unsupported change_kind: {change_kind!r}")


def _parse_explore(
    raw: Any, requested_mode: str
) -> tuple[tuple[Perspective, ...], str]:
    response = _response_mapping(raw, "EXPLORE")
    _require_exact_keys(
        response,
        {"stage", "mode", "perspectives", "visible_output"},
        "EXPLORE",
    )
    if response["stage"] != "EXPLORE" or response["mode"] != requested_mode:
        raise AutoProtocolError("EXPLORE stage/mode mismatch")
    visible_output = _require_nonempty_string(
        response["visible_output"], "EXPLORE.visible_output"
    )
    items = response["perspectives"]
    if not isinstance(items, list) or not items:
        raise AutoProtocolError("EXPLORE.perspectives must be a non-empty list")
    parsed: list[Perspective] = []
    numbers: list[int] = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise AutoProtocolError(f"EXPLORE.perspectives[{index}] must be an object")
        _require_exact_keys(item, {"p_id", "claim", "viable"}, "EXPLORE perspective")
        number = _p_id_number(item["p_id"], f"EXPLORE.perspectives[{index}].p_id")
        claim = _require_nonempty_string(
            item["claim"], f"EXPLORE.perspectives[{index}].claim"
        )
        if not isinstance(item["viable"], bool):
            raise AutoProtocolError(
                f"EXPLORE.perspectives[{index}].viable must be boolean"
            )
        numbers.append(number)
        parsed.append(Perspective(item["p_id"], claim, item["viable"]))
    if numbers != sorted(numbers) or len(numbers) != len(set(numbers)):
        raise AutoProtocolError("EXPLORE P-IDs must be unique and monotonically ordered")
    if not any(item.viable for item in parsed):
        raise AutoProtocolError("EXPLORE returned no viable perspective")
    return tuple(parsed), visible_output


def _parse_deep(raw: Any, selected_p_id: str) -> tuple[str, str, str]:
    response = _response_mapping(raw, "DEEP")
    common = {"stage", "mode", "selected_p_id", "gate", "model", "visible_output"}
    gate = response.get("gate")
    if gate == "NEED_EVIDENCE":
        expected = common | {"evidence_debt"}
    elif gate == "RETURN_TO_EXPLORE":
        expected = common | {"break_point"}
    else:
        expected = common
    _require_exact_keys(response, expected, "DEEP")
    if response["stage"] != "DEEP" or response["mode"] != "DEEP":
        raise AutoProtocolError("DEEP stage/mode mismatch")
    if response["selected_p_id"] != selected_p_id:
        raise AutoProtocolError("DEEP substituted the selected P-ID")
    if gate not in _DEEP_GATES:
        raise AutoProtocolError("DEEP gate is invalid")
    model = _require_nonempty_string(response["model"], "DEEP.model")
    visible_output = _require_nonempty_string(
        response["visible_output"], "DEEP.visible_output"
    )
    if gate == "NEED_EVIDENCE":
        debt = response["evidence_debt"]
        if not isinstance(debt, Mapping):
            raise AutoProtocolError("DEEP.evidence_debt must be an object")
        _require_exact_keys(
            debt,
            {"missing", "dependent_conclusion", "claim_boundary", "cheap_check"},
            "DEEP.evidence_debt",
        )
        for field in ("missing", "dependent_conclusion", "claim_boundary", "cheap_check"):
            _require_nonempty_string(debt[field], f"DEEP.evidence_debt.{field}")
    elif gate == "RETURN_TO_EXPLORE":
        _require_nonempty_string(response["break_point"], "DEEP.break_point")
    return gate, model, visible_output


def _parse_make(raw: Any, selected_p_id: str) -> tuple[str, str]:
    response = _response_mapping(raw, "MAKE")
    _require_exact_keys(
        response,
        {"stage", "mode", "selected_p_id", "artifact", "visible_output"},
        "MAKE",
    )
    if response["stage"] != "MAKE" or response["mode"] != "MAKE":
        raise AutoProtocolError("MAKE stage/mode mismatch")
    if response["selected_p_id"] != selected_p_id:
        raise AutoProtocolError("MAKE substituted the selected P-ID")
    artifact = _require_nonempty_string(response["artifact"], "MAKE.artifact")
    visible_output = _require_nonempty_string(
        response["visible_output"], "MAKE.visible_output"
    )
    return artifact, visible_output


def run_auto(
    task: str,
    context: str,
    source_data: str,
    *,
    adapter: SubjectAdapter | None = None,
    explore_mode: Literal["NORMAL", "RIFT", "360"] = "NORMAL",
) -> AutoResult:
    """Run the smallest deterministic Explore -> Deep -> gated MAKE policy.

    The deterministic selection policy is the lowest numeric viable P-ID.
    ``NEED_EVIDENCE`` and ``RETURN_TO_EXPLORE`` are terminal: MAKE is never
    invoked for either gate.
    """
    task = _require_nonempty_string(task, "task")
    if not isinstance(context, str):
        raise AutoProtocolError("context must be a string")
    source_data = _require_nonempty_string(source_data, "source_data")
    if explore_mode not in _EXPLORE_MODES:
        raise AutoProtocolError("explore_mode is invalid")
    if adapter is None:
        raise AutoProtocolError("an explicit subject adapter is required")

    explore_payload = _common_payload(
        stage="EXPLORE", task=task, context=context, source_data=source_data
    )
    explore_payload["mode"] = explore_mode
    alternatives, explore_visible = _parse_explore(
        adapter.invoke("EXPLORE", explore_payload), explore_mode
    )
    selected = min(
        (item for item in alternatives if item.viable),
        key=lambda item: _p_id_number(item.p_id),
    )
    visible_alternatives = [
        {"p_id": item.p_id, "claim": item.claim, "viable": item.viable}
        for item in alternatives
    ]

    deep_payload = _common_payload(
        stage="DEEP", task=task, context=context, source_data=source_data
    )
    deep_payload.update(
        {
            "mode": "DEEP",
            "selected_p_id": selected.p_id,
            "selected_claim": selected.claim,
            "visible_alternatives": visible_alternatives,
        }
    )
    gate, model, deep_visible = _parse_deep(
        adapter.invoke("DEEP", deep_payload), selected.p_id
    )
    if gate != "MODEL_READY":
        return AutoResult(
            gate=gate,
            selected_p_id=selected.p_id,
            alternatives=alternatives,
            explore_visible_output=explore_visible,
            deep_visible_output=deep_visible,
            final_artifact=None,
            make_visible_output=None,
        )

    make_payload = _common_payload(
        stage="MAKE", task=task, context=context, source_data=source_data
    )
    make_payload.update(
        {
            "mode": "MAKE",
            "selected_p_id": selected.p_id,
            "selected_claim": selected.claim,
            "visible_alternatives": visible_alternatives,
            "model": model,
            "gate": gate,
        }
    )
    artifact, make_visible = _parse_make(
        adapter.invoke("MAKE", make_payload), selected.p_id
    )
    return AutoResult(
        gate=gate,
        selected_p_id=selected.p_id,
        alternatives=alternatives,
        explore_visible_output=explore_visible,
        deep_visible_output=deep_visible,
        final_artifact=artifact,
        make_visible_output=make_visible,
    )
