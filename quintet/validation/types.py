"""
Validation types: shared currency for validation checks across all phases.

ValidationCheckResult is the atomic unit of validation.
ValidationSummary aggregates multiple checks into a coherent picture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ValidationCheckResult:
    """
    Atomic validation result for a single named check.

    This is the "currency" of the validation system:
    every Phase N check returns one of these.

    Fields:
        name: Check name (e.g., "episode_quality", "stress_gates")
        passed: Whether the invariant is satisfied
        warnings: Non-fatal issues to be aware of
        errors: Fatal issues preventing pass
        details: Arbitrary metadata for this check
    """

    name: str
    passed: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_failures(self) -> bool:
        """True if check failed (not passed and has errors)."""
        return (not self.passed) and bool(self.errors)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON/reporting."""
        return {
            "name": self.name,
            "passed": self.passed,
            "warnings": self.warnings,
            "errors": self.errors,
            "details": self.details,
        }


@dataclass
class ValidationSummary:
    """
    Rollup of multiple ValidationCheckResult entries.

    This is what the CLI prints and what higher phases can consume.
    Provides aggregated views over a set of checks.
    """

    checks: List[ValidationCheckResult]

    @property
    def passed_checks(self) -> int:
        """Count of checks that passed."""
        return sum(1 for c in self.checks if c.passed)

    @property
    def warnings_count(self) -> int:
        """Total warning count across all checks."""
        return sum(len(c.warnings) for c in self.checks)

    @property
    def failures(self) -> List[str]:
        """Names of checks that have failures."""
        return [c.name for c in self.checks if c.has_failures]

    @property
    def all_passed(self) -> bool:
        """True if all checks passed."""
        return all(c.passed for c in self.checks)

    @property
    def total_checks(self) -> int:
        """Total number of checks."""
        return len(self.checks)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON/reporting."""
        return {
            "checks": [c.to_dict() for c in self.checks],
            "passed_checks": self.passed_checks,
            "warnings_count": self.warnings_count,
            "failures": self.failures,
            "total_checks": self.total_checks,
        }
