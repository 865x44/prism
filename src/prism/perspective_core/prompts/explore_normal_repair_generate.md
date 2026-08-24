# Schema Repair — Call A: Diagnosis and Candidate Generation

Your previous response had a structural error. Fix it and return valid JSON.

## Error

<<ERROR>>

## Original request

You were asked to diagnose source material and generate candidates.

Source:
```
<<SOURCE>>
```

Objective: <<OBJECTIVE>>

## Output format

Return a single JSON object with exactly these fields:

```json
{
  "diagnosis": {
    "central_problem": "string",
    "search_profile": "string",
    "priority_dimensions": ["string"]
  },
  "candidates": [
    {
      "semantic_core": {
        "central_problem": "string",
        "mechanism": "string",
        "load_bearing_claim": "string",
        "central_object": "string or null",
        "unit_of_analysis": "string or null",
        "system_boundary": "string or null",
        "agency_model": "string or null",
        "temporal_logic": "string or null",
        "key_constraint": "string or null",
        "downstream_consequences": ["string"]
      },
      "preserved": ["string"],
      "default_frame": "string",
      "blind_spot": "string",
      "operator_ids": ["string"],
      "shift": "string",
      "perspective": "string",
      "new_consequences": ["string"],
      "return_path": {
        "dimension_changed": "string",
        "consequence_chain": ["string"],
        "why_it_matters": "string"
      },
      "epistemics": {
        "supported": ["string"],
        "inferred": ["string"],
        "speculative": ["string"],
        "unknown": ["string"],
        "break_condition": ["string"]
      }
    }
  ]
}
```

Return ONLY the JSON object, no additional text.
