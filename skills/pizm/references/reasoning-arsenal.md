# Pizm Reasoning Arsenal

Compact private vocabulary for Pizm passes. Each entry names a move and states what it is for. The arsenal is a memory aid for the reasoning subject, not a checklist: use a move when the material calls for it, name it only when doing so aids the user or the transcript.

## Search moves

- **APPARENT RESOURCE -> HIDDEN POLICY**: What presents itself as a free resource (time, attention, goodwill, data, slack) is produced by some policy that could be otherwise. Find the policy behind the apparent resource.
- **CONSTRAINT VALIDITY**: For each stated constraint, ask whether it is physically real, chosen, inherited, or merely assumed. Invalid constraints silently delete whole territories; testing one can reopen them.
- **STRUCTURAL CONTRADICTION**: Two load-bearing parts of the situation cannot both hold as described. Locating the contradiction precisely often dissolves several fake options at once.
- **DISSOLVED VS RELOCATED**: A problem that "went away" was either dissolved (its generating mechanism removed) or relocated (moved to someone else, later, or elsewhere). Trace where the cost actually sits now.
- **FEEDBACK / DELAY / THRESHOLD**: Many stale models ignore loop structure: which feedbacks dominate, where delays hide, and which thresholds flip behavior qualitatively.
- **STATED VS ENACTED GOAL**: Compare what actors say they optimize with what their behavior reveals they optimize. The gap is usually the most informative variable in the situation.

## Portfolio moves

- **UNIQUE RESIDUE**: What a candidate contributes that nothing else in the field does. Empty residue is a finding about the field, not a defect of the judge.
- **COMPOSITION GAIN**: The something a bundle asserts, explains, predicts, or reveals that no listing of its members with "and" recovers. No gain, no bundle.
- **MEMBER ABLATION**: For each member, state what breaks when it is removed. A member whose removal loses nothing is a passenger; remove it or dissolve the bundle.
- **DYNAMIC CLOSURE**: A territory is closed when its outer shell is genuinely exhausted, not when it becomes tiresome. Track seen versus closed separately; revisit only reopened territories.
- **COST RELOCATION**: A perspective that removes a visible cost while quietly creating an invisible one has not improved the situation; follow the cost to its new address before judging.
- **PRODUCTIVE TENSION**: Live contradiction between members that generates consequences neither yields alone. Tension to preserve and state, not noise to smooth over.

## Critic moves
Wired into the single-model Critic contract (`references/deep-reviewer.md`) and Comparative Review:
- **LOAD-BEARING CLAIM CENSUS**: Enumerate the claims whose failure collapses the model; most claims are decoration, few are load-bearing.
- **SUPPORTED|INFERRED|SPECULATIVE|UNKNOWN**: Epistemic labeling of every load-bearing claim against the source material.
- **INDEPENDENT COUNTERMODEL**: Construct the strongest model incompatible with the candidate, then ask what observation would separate them.
- **UNSUPPORTED SPECIFICITY**: Precision (numbers, dates, named mechanisms) exceeding what the source supports; specificity borrowed from nowhere is a hallucination signature.
- **EPISTEMIC LAUNDERING**: Speculation restated as inference, or inference restated as supported fact; catch status upgrades that happen between sentences.
- **ROUND-TRIP SKELETON**: Restate the model's prediction in the source's own terms and check it still lands; a model that cannot survive translation back is decorative.
- **CHEAPEST DISCRIMINATING TEST**: The smallest observation, query, or experiment that would distinguish the model from its rivals; prefer cheap tests over elaborate ones.

## Anti-cargo-cult rule

Do not instantiate a method merely because it exists in the arsenal. There is no output quota per technique, and "no useful application of this move" is a valid outcome. The arsenal defines no method-specific agents and no public modes: it is vocabulary available inside existing passes, never a reason to create a new one.

<!-- migration-notes
arsenal: shared vocabulary across search-field, portfolio, deep-review, and comparison stages
critic moves: wired into deep-reviewer.md and comparative reasoning
-->
