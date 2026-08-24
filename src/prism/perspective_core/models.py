"""Core data models for Perspective Core v0.

Implements replan §6 and execution contract frozen APIs.
Standard-library dataclasses only; no new dependencies.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Literal


# ─────────────────────────────────────────────────────────────────────────────
# Constraint Ledger (§6.1)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ConstraintEntry:
    constraint_id: str
    value: str
    kind: Literal["hard", "preference"]
    provenance_turn: str | None = None
    status: Literal["active", "superseded"] = "active"

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_id": self.constraint_id,
            "value": self.value,
            "kind": self.kind,
            "provenance_turn": self.provenance_turn,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConstraintEntry:
        if data.get("kind") not in ("hard", "preference"):
            raise ValueError(f"Invalid kind: {data.get('kind')}")
        if data.get("status") not in ("active", "superseded"):
            raise ValueError(f"Invalid status: {data.get('status')}")
        return cls(
            constraint_id=data["constraint_id"],
            value=data["value"],
            kind=data["kind"],
            provenance_turn=data.get("provenance_turn"),
            status=data["status"],
        )


@dataclass
class ConstraintLedger:
    entries: list[ConstraintEntry] = field(default_factory=list)

    def add(
        self,
        *,
        constraint_id: str,
        value: str,
        kind: Literal["hard", "preference"],
        provenance_turn: str | None = None,
    ) -> None:
        """Add constraint; supersedes prior entry with same constraint_id."""
        # Supersede existing active entry with same ID
        for entry in self.entries:
            if entry.constraint_id == constraint_id and entry.status == "active":
                entry.status = "superseded"

        # Append new active entry
        self.entries.append(
            ConstraintEntry(
                constraint_id=constraint_id,
                value=value,
                kind=kind,
                provenance_turn=provenance_turn,
                status="active",
            )
        )

    def active_entries(self) -> list[ConstraintEntry]:
        """Return only active constraints."""
        return [e for e in self.entries if e.status == "active"]

    def to_dict(self) -> dict[str, Any]:
        return {"entries": [e.to_dict() for e in self.entries]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConstraintLedger:
        return cls(entries=[ConstraintEntry.from_dict(e) for e in data.get("entries", [])])


# ─────────────────────────────────────────────────────────────────────────────
# Return Path and Epistemics (§6.4 dependencies)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ReturnPath:
    dimension_changed: str
    consequence_chain: list[str]
    why_it_matters: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_changed": self.dimension_changed,
            "consequence_chain": self.consequence_chain,
            "why_it_matters": self.why_it_matters,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReturnPath:
        return cls(
            dimension_changed=data["dimension_changed"],
            consequence_chain=data["consequence_chain"],
            why_it_matters=data["why_it_matters"],
        )


@dataclass
class Epistemics:
    supported: list[str]
    inferred: list[str]
    speculative: list[str]
    unknown: list[str]
    break_condition: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "supported": self.supported,
            "inferred": self.inferred,
            "speculative": self.speculative,
            "unknown": self.unknown,
            "break_condition": self.break_condition,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Epistemics:
        return cls(
            supported=data.get("supported", []),
            inferred=data.get("inferred", []),
            speculative=data.get("speculative", []),
            unknown=data.get("unknown", []),
            break_condition=data.get("break_condition", []),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Diagnosis (§6.9 dependency)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Diagnosis:
    central_problem: str
    search_profile: str
    priority_dimensions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "central_problem": self.central_problem,
            "search_profile": self.search_profile,
            "priority_dimensions": self.priority_dimensions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Diagnosis:
        return cls(
            central_problem=data["central_problem"],
            search_profile=data["search_profile"],
            priority_dimensions=data["priority_dimensions"],
        )


# ─────────────────────────────────────────────────────────────────────────────
# PerspectiveRequest (§6.2)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class PerspectiveRequest:
    source: str
    objective: str
    mode: Literal["normal", "rift", "360"]
    context: str | None = None
    session_id: str | None = None
    constraint_ledger: ConstraintLedger = field(default_factory=ConstraintLedger)
    must_not_claim: list[str] = field(default_factory=list)
    candidate_budget: int = 8


# ─────────────────────────────────────────────────────────────────────────────
# SemanticCore (§6.3)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class SemanticCore:
    central_problem: str
    mechanism: str
    load_bearing_claim: str
    central_object: str | None = None
    unit_of_analysis: str | None = None
    system_boundary: str | None = None
    agency_model: str | None = None
    temporal_logic: str | None = None
    key_constraint: str | None = None
    downstream_consequences: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "central_problem": self.central_problem,
            "mechanism": self.mechanism,
            "load_bearing_claim": self.load_bearing_claim,
            "central_object": self.central_object,
            "unit_of_analysis": self.unit_of_analysis,
            "system_boundary": self.system_boundary,
            "agency_model": self.agency_model,
            "temporal_logic": self.temporal_logic,
            "key_constraint": self.key_constraint,
            "downstream_consequences": self.downstream_consequences,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SemanticCore:
        return cls(
            central_problem=data["central_problem"],
            mechanism=data["mechanism"],
            load_bearing_claim=data["load_bearing_claim"],
            central_object=data.get("central_object"),
            unit_of_analysis=data.get("unit_of_analysis"),
            system_boundary=data.get("system_boundary"),
            agency_model=data.get("agency_model"),
            temporal_logic=data.get("temporal_logic"),
            key_constraint=data.get("key_constraint"),
            downstream_consequences=data.get("downstream_consequences", []),
        )


# ─────────────────────────────────────────────────────────────────────────────
# PerspectiveCandidate (§6.4)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class PerspectiveCandidate:
    candidate_id: str
    semantic_core: SemanticCore
    preserved: list[str]
    default_frame: str
    blind_spot: str
    operator_ids: list[str]
    shift: str
    perspective: str
    new_consequences: list[str]
    return_path: ReturnPath
    epistemics: Epistemics

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "semantic_core": self.semantic_core.to_dict(),
            "preserved": self.preserved,
            "default_frame": self.default_frame,
            "blind_spot": self.blind_spot,
            "operator_ids": self.operator_ids,
            "shift": self.shift,
            "perspective": self.perspective,
            "new_consequences": self.new_consequences,
            "return_path": self.return_path.to_dict(),
            "epistemics": self.epistemics.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PerspectiveCandidate:
        return cls(
            candidate_id=data["candidate_id"],
            semantic_core=SemanticCore.from_dict(data["semantic_core"]),
            preserved=data["preserved"],
            default_frame=data["default_frame"],
            blind_spot=data["blind_spot"],
            operator_ids=data["operator_ids"],
            shift=data["shift"],
            perspective=data["perspective"],
            new_consequences=data["new_consequences"],
            return_path=ReturnPath.from_dict(data["return_path"]),
            epistemics=Epistemics.from_dict(data["epistemics"]),
        )


# ─────────────────────────────────────────────────────────────────────────────
# ValidationIssue (§6.5)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ValidationIssue:
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationIssue:
        return cls(code=data["code"], message=data["message"])


# ─────────────────────────────────────────────────────────────────────────────
# MergeTarget (§6.6)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class MergeTarget:
    kind: Literal["candidate", "perspective"]
    target_id: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "target_id": self.target_id}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MergeTarget:
        if data.get("kind") not in ("candidate", "perspective"):
            raise ValueError(f"Invalid MergeTarget kind: {data.get('kind')}")
        return cls(kind=data["kind"], target_id=data["target_id"])


# ─────────────────────────────────────────────────────────────────────────────
# SelectionRecord (§6.7)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class SelectionRecord:
    candidate_id: str
    admissible: bool
    constraint_failures: list[str]
    structurally_distinct: bool
    novelty_dimensions: list[str]
    nearest_candidate_id: str | None
    nearest_existing_p_id: str | None
    standalone_quality: Literal["strong", "borderline", "weak"]
    marginal_contribution: Literal["high", "medium", "low", "none"]
    disposition: Literal["KEEP", "BORDERLINE", "MERGE", "DROP"]
    merge_target: MergeTarget | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "admissible": self.admissible,
            "constraint_failures": self.constraint_failures,
            "structurally_distinct": self.structurally_distinct,
            "novelty_dimensions": self.novelty_dimensions,
            "nearest_candidate_id": self.nearest_candidate_id,
            "nearest_existing_p_id": self.nearest_existing_p_id,
            "standalone_quality": self.standalone_quality,
            "marginal_contribution": self.marginal_contribution,
            "disposition": self.disposition,
            "merge_target": self.merge_target.to_dict() if self.merge_target else None,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SelectionRecord:
        if data.get("standalone_quality") not in ("strong", "borderline", "weak"):
            raise ValueError(f"Invalid standalone_quality: {data.get('standalone_quality')}")
        if data.get("marginal_contribution") not in ("high", "medium", "low", "none"):
            raise ValueError(f"Invalid marginal_contribution: {data.get('marginal_contribution')}")
        if data.get("disposition") not in ("KEEP", "BORDERLINE", "MERGE", "DROP"):
            raise ValueError(f"Invalid disposition: {data.get('disposition')}")

        merge_target_data = data.get("merge_target")
        merge_target = MergeTarget.from_dict(merge_target_data) if merge_target_data else None

        return cls(
            candidate_id=data["candidate_id"],
            admissible=data["admissible"],
            constraint_failures=data["constraint_failures"],
            structurally_distinct=data["structurally_distinct"],
            novelty_dimensions=data["novelty_dimensions"],
            nearest_candidate_id=data.get("nearest_candidate_id"),
            nearest_existing_p_id=data.get("nearest_existing_p_id"),
            standalone_quality=data["standalone_quality"],
            marginal_contribution=data["marginal_contribution"],
            disposition=data["disposition"],
            merge_target=merge_target,
            reason=data["reason"],
        )


# ─────────────────────────────────────────────────────────────────────────────
# PerspectiveIdentity and PerspectiveState (§6.8)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class PerspectiveIdentity:
    p_id: str
    candidate_id: str
    identity_core: SemanticCore

    def to_dict(self) -> dict[str, Any]:
        return {
            "p_id": self.p_id,
            "candidate_id": self.candidate_id,
            "identity_core": self.identity_core.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PerspectiveIdentity:
        return cls(
            p_id=data["p_id"],
            candidate_id=data["candidate_id"],
            identity_core=SemanticCore.from_dict(data["identity_core"]),
        )


@dataclass
class PerspectiveState:
    identity: PerspectiveIdentity
    current_version: int
    epistemics: Epistemics
    deep_refs: list[str]
    terminal_state: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity.to_dict(),
            "current_version": self.current_version,
            "epistemics": self.epistemics.to_dict(),
            "deep_refs": self.deep_refs,
            "terminal_state": self.terminal_state,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PerspectiveState:
        return cls(
            identity=PerspectiveIdentity.from_dict(data["identity"]),
            current_version=data["current_version"],
            epistemics=Epistemics.from_dict(data["epistemics"]),
            deep_refs=data["deep_refs"],
            terminal_state=data.get("terminal_state"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# PassRecord (§6.9)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class PassRecord:
    pass_id: str
    mode: Literal["normal", "rift", "360"]
    created_at: str
    diagnosis: Diagnosis
    candidates: list[PerspectiveCandidate]
    selections: list[SelectionRecord]
    kept_p_ids: list[str]
    provider_invocation_ids: list[str]
    trace_ref: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass_id": self.pass_id,
            "mode": self.mode,
            "created_at": self.created_at,
            "diagnosis": self.diagnosis.to_dict(),
            "candidates": [c.to_dict() for c in self.candidates],
            "selections": [s.to_dict() for s in self.selections],
            "kept_p_ids": self.kept_p_ids,
            "provider_invocation_ids": self.provider_invocation_ids,
            "trace_ref": self.trace_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PassRecord:
        if data.get("mode") not in ("normal", "rift", "360"):
            raise ValueError(f"Invalid mode: {data.get('mode')}")
        return cls(
            pass_id=data["pass_id"],
            mode=data["mode"],
            created_at=data["created_at"],
            diagnosis=Diagnosis.from_dict(data["diagnosis"]),
            candidates=[PerspectiveCandidate.from_dict(c) for c in data["candidates"]],
            selections=[SelectionRecord.from_dict(s) for s in data["selections"]],
            kept_p_ids=data["kept_p_ids"],
            provider_invocation_ids=data["provider_invocation_ids"],
            trace_ref=data["trace_ref"],
        )


# ─────────────────────────────────────────────────────────────────────────────
# DeepRunRef (§6.10)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class DeepRunRef:
    deep_id: str
    p_id: str
    terminal_state: Literal["MODEL_READY", "NEED_EVIDENCE", "RETURN_TO_EXPLORE"]
    trace_ref: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "deep_id": self.deep_id,
            "p_id": self.p_id,
            "terminal_state": self.terminal_state,
            "trace_ref": self.trace_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeepRunRef:
        if data.get("terminal_state") not in ("MODEL_READY", "NEED_EVIDENCE", "RETURN_TO_EXPLORE"):
            raise ValueError(f"Invalid terminal_state: {data.get('terminal_state')}")
        return cls(
            deep_id=data["deep_id"],
            p_id=data["p_id"],
            terminal_state=data["terminal_state"],
            trace_ref=data["trace_ref"],
        )


# ─────────────────────────────────────────────────────────────────────────────
# PerspectiveSession (§6.10)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class PerspectiveSession:
    session_id: str
    source_hash: str
    objective: str
    constraint_ledger: ConstraintLedger
    next_p_number: int
    perspectives: dict[str, PerspectiveState]
    passes: list[PassRecord]
    deep_runs: list[DeepRunRef]

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "source_hash": self.source_hash,
            "objective": self.objective,
            "constraint_ledger": self.constraint_ledger.to_dict(),
            "next_p_number": self.next_p_number,
            "perspectives": {k: v.to_dict() for k, v in self.perspectives.items()},
            "passes": [p.to_dict() for p in self.passes],
            "deep_runs": [d.to_dict() for d in self.deep_runs],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PerspectiveSession:
        return cls(
            session_id=data["session_id"],
            source_hash=data["source_hash"],
            objective=data["objective"],
            constraint_ledger=ConstraintLedger.from_dict(data["constraint_ledger"]),
            next_p_number=data["next_p_number"],
            perspectives={
                k: PerspectiveState.from_dict(v) for k, v in data["perspectives"].items()
            },
            passes=[PassRecord.from_dict(p) for p in data["passes"]],
            deep_runs=[DeepRunRef.from_dict(d) for d in data["deep_runs"]],
        )


def compute_source_hash(source: str) -> str:
    """Compute SHA-256 hash of source text."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# ProviderResult (§8)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ProviderResult:
    invocation_id: str
    stage: str
    raw_text: str
    model: str
    transport: str
    duration_ms: int
    exit_code: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "invocation_id": self.invocation_id,
            "stage": self.stage,
            "raw_text": self.raw_text,
            "model": self.model,
            "transport": self.transport,
            "duration_ms": self.duration_ms,
            "exit_code": self.exit_code,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Deep contracts (§10)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class DeepDevelopment:
    p_id: str
    semantic_lock_echo: SemanticCore
    developed_model: str
    what_became_more_precise: list[str]
    assumptions: list[str]
    supporting_basis: list[str]
    evidence_missing: list[str]
    unknowns: list[str]
    strongest_countermodel: str | None
    break_conditions: list[str]
    downstream_implications: list[str]
    optional_analysis: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "p_id": self.p_id,
            "semantic_lock_echo": self.semantic_lock_echo.to_dict(),
            "developed_model": self.developed_model,
            "what_became_more_precise": self.what_became_more_precise,
            "assumptions": self.assumptions,
            "supporting_basis": self.supporting_basis,
            "evidence_missing": self.evidence_missing,
            "unknowns": self.unknowns,
            "strongest_countermodel": self.strongest_countermodel,
            "break_conditions": self.break_conditions,
            "downstream_implications": self.downstream_implications,
            "optional_analysis": self.optional_analysis,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeepDevelopment:
        return cls(
            p_id=data["p_id"],
            semantic_lock_echo=SemanticCore.from_dict(data["semantic_lock_echo"]),
            developed_model=data["developed_model"],
            what_became_more_precise=data["what_became_more_precise"],
            assumptions=data["assumptions"],
            supporting_basis=data["supporting_basis"],
            evidence_missing=data["evidence_missing"],
            unknowns=data["unknowns"],
            strongest_countermodel=data.get("strongest_countermodel"),
            break_conditions=data["break_conditions"],
            downstream_implications=data["downstream_implications"],
            optional_analysis=data.get("optional_analysis"),
        )


@dataclass
class DeepReview:
    identity_preserved: bool
    identity_drift: list[str]
    load_bearing_claim: str
    strongest_objection: str
    objection_target: str
    objection_is_load_bearing: bool
    counterevidence: list[str]
    evidence_debt: list[str]
    rebuild_required: bool
    rebuild_instructions: list[str]
    terminal_state: Literal["MODEL_READY", "NEED_EVIDENCE", "RETURN_TO_EXPLORE"]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity_preserved": self.identity_preserved,
            "identity_drift": self.identity_drift,
            "load_bearing_claim": self.load_bearing_claim,
            "strongest_objection": self.strongest_objection,
            "objection_target": self.objection_target,
            "objection_is_load_bearing": self.objection_is_load_bearing,
            "counterevidence": self.counterevidence,
            "evidence_debt": self.evidence_debt,
            "rebuild_required": self.rebuild_required,
            "rebuild_instructions": self.rebuild_instructions,
            "terminal_state": self.terminal_state,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeepReview:
        if data.get("terminal_state") not in ("MODEL_READY", "NEED_EVIDENCE", "RETURN_TO_EXPLORE"):
            raise ValueError(f"Invalid terminal_state: {data.get('terminal_state')}")
        return cls(
            identity_preserved=data["identity_preserved"],
            identity_drift=data["identity_drift"],
            load_bearing_claim=data["load_bearing_claim"],
            strongest_objection=data["strongest_objection"],
            objection_target=data["objection_target"],
            objection_is_load_bearing=data["objection_is_load_bearing"],
            counterevidence=data["counterevidence"],
            evidence_debt=data["evidence_debt"],
            rebuild_required=data["rebuild_required"],
            rebuild_instructions=data["rebuild_instructions"],
            terminal_state=data["terminal_state"],
            rationale=data["rationale"],
        )


@dataclass
class DeepRebuildResult:
    development: DeepDevelopment
    final_review: DeepReview

    def to_dict(self) -> dict[str, Any]:
        return {
            "development": self.development.to_dict(),
            "final_review": self.final_review.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeepRebuildResult:
        return cls(
            development=DeepDevelopment.from_dict(data["development"]),
            final_review=DeepReview.from_dict(data["final_review"]),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Run result contracts (execution contract frozen APIs)
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ExploreRunResult:
    run_id: str
    session_id: str
    kept: list[PerspectiveState]
    selections: list[SelectionRecord]
    rendered: str
    outcome: Literal["OK", "NO_NEW_STRONG_TERRITORY_FOUND_THIS_PASS"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "session_id": self.session_id,
            "kept": [k.to_dict() for k in self.kept],
            "selections": [s.to_dict() for s in self.selections],
            "rendered": self.rendered,
            "outcome": self.outcome,
        }


@dataclass
class DeepRunResult:
    run_id: str
    deep_id: str
    p_id: str
    development: DeepDevelopment
    review: DeepReview
    rebuilt_development: DeepDevelopment | None
    terminal_state: Literal["MODEL_READY", "NEED_EVIDENCE", "RETURN_TO_EXPLORE"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "deep_id": self.deep_id,
            "p_id": self.p_id,
            "development": self.development.to_dict(),
            "review": self.review.to_dict(),
            "rebuilt_development": (
                self.rebuilt_development.to_dict() if self.rebuilt_development else None
            ),
            "terminal_state": self.terminal_state,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Structural validation helpers (§6.5)
# ─────────────────────────────────────────────────────────────────────────────


def validate_candidates(
    candidates: list[PerspectiveCandidate],
) -> dict[str, list[ValidationIssue]]:
    """Validate candidate structure; returns issues by candidate_id."""
    issues: dict[str, list[ValidationIssue]] = {}

    # Check unique IDs
    seen_ids: set[str] = set()
    for c in candidates:
        if c.candidate_id in seen_ids:
            issues.setdefault(c.candidate_id, []).append(
                ValidationIssue(code="DUPLICATE_CANDIDATE_ID", message=f"Duplicate candidate_id: {c.candidate_id}")
            )
        seen_ids.add(c.candidate_id)

    return issues


def validate_selections(
    candidates: list[PerspectiveCandidate],
    selections: list[SelectionRecord],
    existing_p_ids: set[str] | None = None,
) -> dict[str, list[ValidationIssue]]:
    """Validate selection records against candidates."""
    issues: dict[str, list[ValidationIssue]] = {}
    existing_p_ids = existing_p_ids or set()

    candidate_ids = {c.candidate_id for c in candidates}

    # Check every candidate has exactly one selection
    selected_ids = [s.candidate_id for s in selections]
    for cid in candidate_ids:
        count = selected_ids.count(cid)
        if count == 0:
            issues.setdefault(cid, []).append(
                ValidationIssue(code="MISSING_SELECTION", message=f"No selection for candidate {cid}")
            )
        elif count > 1:
            issues.setdefault(cid, []).append(
                ValidationIssue(code="DUPLICATE_SELECTION", message=f"Multiple selections for candidate {cid}")
            )

    # Validate each selection
    for sel in selections:
        if sel.candidate_id not in candidate_ids:
            issues.setdefault(sel.candidate_id, []).append(
                ValidationIssue(
                    code="UNKNOWN_CANDIDATE",
                    message=f"Selection references unknown candidate {sel.candidate_id}",
                )
            )

        # Validate KEEP disposition coherence
        if sel.disposition == "KEEP":
            if not sel.admissible:
                issues.setdefault(sel.candidate_id, []).append(
                    ValidationIssue(
                        code="INADMISSIBLE_KEEP",
                        message=f"Candidate {sel.candidate_id} cannot be KEEP when admissible is False",
                    )
                )
            if sel.constraint_failures:
                issues.setdefault(sel.candidate_id, []).append(
                    ValidationIssue(
                        code="KEEP_WITH_CONSTRAINT_FAILURES",
                        message=f"Candidate {sel.candidate_id} cannot be KEEP with constraint failures",
                    )
                )

        # Validate non-MERGE dispositions do not carry merge_target
        if sel.disposition != "MERGE" and sel.merge_target is not None:
            issues.setdefault(sel.candidate_id, []).append(
                ValidationIssue(
                    code="UNEXPECTED_MERGE_TARGET",
                    message=f"Candidate {sel.candidate_id} has disposition {sel.disposition} but specifies merge_target",
                )
            )

        # Validate MERGE target
        if sel.disposition == "MERGE":
            if sel.merge_target is None:
                issues.setdefault(sel.candidate_id, []).append(
                    ValidationIssue(code="MERGE_WITHOUT_TARGET", message="MERGE disposition requires merge_target")
                )
            else:
                if sel.merge_target.kind == "candidate":
                    if sel.merge_target.target_id not in candidate_ids:
                        issues.setdefault(sel.candidate_id, []).append(
                            ValidationIssue(
                                code="INVALID_MERGE_TARGET",
                                message=f"Merge target candidate {sel.merge_target.target_id} not found",
                            )
                        )
                    if sel.merge_target.target_id == sel.candidate_id:
                        issues.setdefault(sel.candidate_id, []).append(
                            ValidationIssue(code="MERGE_SELF", message="Candidate cannot merge with itself")
                        )
                elif sel.merge_target.kind == "perspective":
                    if sel.merge_target.target_id not in existing_p_ids:
                        issues.setdefault(sel.candidate_id, []).append(
                            ValidationIssue(
                                code="INVALID_MERGE_TARGET",
                                message=f"Merge target P-ID {sel.merge_target.target_id} not found",
                            )
                        )

    return issues
