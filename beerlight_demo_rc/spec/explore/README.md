# E3 fixture-local lower-bound anchors

Status: `PROVISIONAL_FIXTURE_ANCHORS`.

`e3_known_supported_territories.json` records only the concrete territories
already supported by the reconciled E3 setup. It is invisible to the subject
and available only to fixture tests/evaluator packet construction. It is not a
global quota, a required card count, or a replacement for `COVERAGE_BREADTH`.

`e3_fake_breadth_regression.json` is an offline, deliberately redundant output
with one annotated anchor and nine concrete omissions. The deterministic check
can therefore fail this fake-breadth regression without inferring an exhaustive
set of possible territory or changing any E1-E12 body.
