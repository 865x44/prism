"""Provider-free Beerlight DEMO_RC harness boundary.

This package is deliberately isolated from ``prism.runtime`` and
``prism.slice``.  It records and validates material-run evidence; it does not
define Beerlight semantics or make network/provider calls.
"""

from .fixtures import FixtureValidationError, load_fixture, validate_fixture
from .provider import DisabledProvider, ProviderCallsDisabled, SubjectProvider
from .records import RunRecordValidationError, write_run_record

__all__ = [
    "DisabledProvider",
    "FixtureValidationError",
    "ProviderCallsDisabled",
    "RunRecordValidationError",
    "SubjectProvider",
    "load_fixture",
    "validate_fixture",
    "write_run_record",
]
