# Schema Repair — RIFT Call B: Semantic Selection

Your previous response had a structural error. Fix it and return valid JSON.

## Error

<<ERROR>>

## Original request

You were asked to evaluate RIFT candidates with donor-vocabulary ablation and return exactly one selection per candidate.

## Output format

Return a JSON array:

```json
[
  {
    "candidate_id": "string",
    "admissible": true,
    "constraint_failures": [],
    "structurally_distinct": true,
    "novelty_dimensions": ["string"],
    "nearest_candidate_id": "string or null",
    "nearest_existing_p_id": "string or null",
    "standalone_quality": "strong|borderline|weak",
    "marginal_contribution": "high|medium|low|none",
    "disposition": "KEEP|BORDERLINE|MERGE|DROP",
    "merge_target": null,
    "reason": "string"
  }
]
```

`merge_target` is null unless disposition is MERGE, in which case:

```json
{
  "kind": "candidate|perspective",
  "target_id": "string"
}
```

Return ONLY the JSON array, no additional text.
