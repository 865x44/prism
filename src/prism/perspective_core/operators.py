"""Operator registry for Perspective Core v0.

Implements replan §25 — 13 seed operators with card fields.
Operator routing is advisory; free-lane candidates are first-class.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OperatorCard:
    """A search heuristic card for candidate generation."""

    id: str
    family: str
    instruction: str
    useful_when: str
    avoid_when: str
    required_return: str
    common_counterfeit: str
    positive_example: str
    negative_example: str


# ─────────────────────────────────────────────────────────────────────────────
# Seed operators (replan §25)
# ─────────────────────────────────────────────────────────────────────────────

OPERATORS: list[OperatorCard] = [
    OperatorCard(
        id="rename_by_actual_function",
        family="reframe",
        instruction="Replace the nominal label with what the system actually does.",
        useful_when="The stated purpose diverges from observed behaviour.",
        avoid_when="The label is already operationally accurate.",
        required_return="Renamed mechanism plus downstream consequence chain.",
        common_counterfeit="Synonym swap that preserves the same model.",
        positive_example="'Education' → 'credential sorting'.",
        negative_example="'Education' → 'learning facilitation'.",
    ),
    OperatorCard(
        id="invert_product_and_byproduct",
        family="reframe",
        instruction="Swap what the system produces intentionally with what it produces incidentally.",
        useful_when="The intended output is less load-bearing than a side effect.",
        avoid_when="Side effects are genuinely negligible.",
        required_return="Inverted causal chain with new primary and secondary outputs.",
        common_counterfeit="Relabelling without changing the causal model.",
        positive_example="Social media: product = connection, byproduct = attention capture → flip.",
        negative_example="Stating the same outputs in reverse order.",
    ),
    OperatorCard(
        id="extend_to_terminal_state",
        family="scale",
        instruction="Follow the mechanism to its logical endpoint.",
        useful_when="Intermediate equilibria mask the true attractor.",
        avoid_when="The terminal state is physically unreachable or undefined.",
        required_return="Terminal state description plus path to reach it.",
        common_counterfeit="Extrapolation that merely restates the current trend.",
        positive_example="Compound interest → infinite concentration without redistribution mechanism.",
        negative_example="Current trend continues at current rate.",
    ),
    OperatorCard(
        id="materialize_abstraction",
        family="ground",
        instruction="Replace abstract entities with concrete instances or physical substrate.",
        useful_when="Abstraction hides load-bearing implementation detail.",
        avoid_when="The abstraction is the actual unit of analysis.",
        required_return="Concrete substrate plus what changes when materialized.",
        common_counterfeit="Adding an example without changing the model.",
        positive_example="'The market decides' → specific order-matching algorithm and latency arbitrage.",
        negative_example="'The market decides' → 'buyers and sellers decide'.",
    ),
    OperatorCard(
        id="construct_counterfactual",
        family="contrast",
        instruction="Build the nearest world where one key assumption is false.",
        useful_when="The default frame treats contingent facts as necessary.",
        avoid_when="The assumption is physically or logically necessary.",
        required_return="Counterfactual world plus divergent consequence chain.",
        common_counterfeit="Fantasy world that changes too many variables at once.",
        positive_example="Remove limited liability → trace how risk allocation changes corporate behaviour.",
        negative_example="Imagine a world where humans are altruistic.",
    ),
    OperatorCard(
        id="find_missing_variable",
        family="gap",
        instruction="Identify what the current model does not account for.",
        useful_when="The model is internally consistent but externally incomplete.",
        avoid_when="The model is already comprehensive for its stated scope.",
        required_return="Missing variable plus how its inclusion changes the model.",
        common_counterfeit="Adding noise variables that do not alter predictions.",
        positive_example="Economic model omits ecological carrying capacity.",
        negative_example="Adding more demographic variables to an already detailed model.",
    ),
    OperatorCard(
        id="find_break_condition",
        family="stress",
        instruction="Determine when the mechanism stops working or inverts.",
        useful_when="The model assumes stability without stating boundary conditions.",
        avoid_when="Break conditions are already well-characterised.",
        required_return="Break condition plus what happens at and beyond it.",
        common_counterfeit="Trivial failure (system stops existing).",
        positive_example="Feedback loop breaks when signal delay exceeds adaptation window.",
        negative_example="System fails when it runs out of resources.",
    ),
    OperatorCard(
        id="follow_incentive_to_exploit",
        family="agency",
        instruction="Trace who benefits from the current arrangement and how they would defend it.",
        useful_when="Stated rationale may mask incentive structure.",
        avoid_when="No agent has meaningful discretion or benefit.",
        required_return="Beneficiary, mechanism of benefit, and defence strategy.",
        common_counterfeit="Generic 'those in power benefit' without mechanism.",
        positive_example="Insurance companies profit from claim complexity → invest in obfuscation.",
        negative_example="Rich people benefit from being rich.",
    ),
    OperatorCard(
        id="redistribute_risk",
        family="agency",
        instruction="Trace who bears the downside and whether it matches who captures the upside.",
        useful_when="Risk and reward appear misaligned.",
        avoid_when="Risk distribution is already symmetric with reward.",
        required_return="Risk bearer, reward capturee, and asymmetry mechanism.",
        common_counterfeit="Stating that risk exists without tracing its distribution.",
        positive_example="Gig economy: platform captures upside, worker bears demand risk.",
        negative_example="Investors bear investment risk.",
    ),
    OperatorCard(
        id="remove_stated_intent",
        family="reframe",
        instruction="Analyse the system as if no one intended its current form.",
        useful_when="Stated intent obscures emergent or evolutionary dynamics.",
        avoid_when="Intent is operationally verifiable and load-bearing.",
        required_return="Emergent explanation plus selection pressure that produced current state.",
        common_counterfeit="Conspiracy removal without providing emergent alternative.",
        positive_example="Bureaucratic complexity: not sabotage but evolutionary accumulation of failure responses.",
        negative_example="They designed it this way → they did not design it this way.",
    ),
    OperatorCard(
        id="shift_system_boundary",
        family="scale",
        instruction="Expand or contract what counts as inside the system.",
        useful_when="Boundary placement hides load-bearing inputs or outputs.",
        avoid_when="Boundary is physically or institutionally fixed.",
        required_return="New boundary plus what enters or exits the model.",
        common_counterfeit="Boundary shift that adds no new causal elements.",
        positive_example="Include supply chain externalities inside firm cost model.",
        negative_example="Add more departments to an org chart.",
    ),
    OperatorCard(
        id="replace_average_with_distribution",
        family="ground",
        instruction="Replace aggregate statistics with the underlying distribution.",
        useful_when="Averages hide load-bearing variance or bimodality.",
        avoid_when="Distribution is genuinely unimodal and narrow.",
        required_return="Distribution shape plus what changes when variance is visible.",
        common_counterfeit="Stating the mean and median without analytical consequence.",
        positive_example="'Average income' → power-law distribution with median far below mean.",
        negative_example="Average is X, median is Y.",
    ),
    OperatorCard(
        id="contrast_with_default",
        family="contrast",
        instruction="Compare the current state against a plausible alternative default.",
        useful_when="Current state appears natural because no alternative is visible.",
        avoid_when="Current state is genuinely the only feasible option.",
        required_return="Alternative default plus divergence from current state.",
        common_counterfeit="Comparing against an impossible or absurd alternative.",
        positive_example="Default retirement age 65 → contrast with no fixed retirement age.",
        negative_example="Democracy → contrast with rule by aliens.",
    ),
]


def operator_by_id(operator_id: str) -> OperatorCard | None:
    """Look up an operator by its ID.

    Args:
        operator_id: Operator identifier

    Returns:
        OperatorCard if found, None otherwise
    """
    for op in OPERATORS:
        if op.id == operator_id:
            return op
    return None


def all_operator_ids() -> list[str]:
    """Return all registered operator IDs."""
    return [op.id for op in OPERATORS]
