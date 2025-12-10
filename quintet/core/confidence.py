"""
Parse vs Validation Confidence Types
====================================

Separates confidence into two components:
- ParseConfidence: how well we understand the problem
- ValidationConfidence: how well we verified the solution

Routing uses min(parse, validation) to prevent overconfidence when one is low.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any


@dataclass
class ParseConfidence:
    """
    Confidence that we correctly understood the problem.

    Low parse confidence + high validation confidence = DANGER:
    we're confidently verifying the wrong thing.
    """
    syntax_score: float = 0.5  # 0.0-1.0: valid structure?
    semantic_score: float = 0.5  # 0.0-1.0: intent clear?
    completeness_score: float = 0.5  # 0.0-1.0: all info present?

    details: Optional[Dict[str, Any]] = field(default_factory=dict)

    @property
    def combined(self) -> float:
        """Simple average of components."""
        return (self.syntax_score + self.semantic_score + self.completeness_score) / 3.0

    @property
    def minimum(self) -> float:
        """Bottleneck: lowest component score."""
        return min(self.syntax_score, self.semantic_score, self.completeness_score)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "syntax_score": self.syntax_score,
            "semantic_score": self.semantic_score,
            "completeness_score": self.completeness_score,
            "combined": self.combined,
            "minimum": self.minimum,
            "details": self.details or {},
        }


@dataclass
class ValidationConfidence:
    """
    Confidence that our solution is correct.

    Measured across symbolic, numeric, structural, and diversity of methods.
    High validation confidence with low parse confidence indicates verification
    of the wrong problem.
    """
    symbolic_score: float = 0.5  # 0.0-1.0: symbolic checks?
    numeric_score: float = 0.5  # 0.0-1.0: numerical verification?
    structural_score: float = 0.5  # 0.0-1.0: bounds/sanity checks?
    diversity_score: float = 0.5  # 0.0-1.0: method diversity?

    details: Optional[Dict[str, Any]] = field(default_factory=dict)

    @property
    def combined(self) -> float:
        """Simple average of components."""
        return (self.symbolic_score + self.numeric_score +
                self.structural_score + self.diversity_score) / 4.0

    @property
    def minimum(self) -> float:
        """Bottleneck: lowest component score."""
        return min(self.symbolic_score, self.numeric_score,
                   self.structural_score, self.diversity_score)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbolic_score": self.symbolic_score,
            "numeric_score": self.numeric_score,
            "structural_score": self.structural_score,
            "diversity_score": self.diversity_score,
            "combined": self.combined,
            "minimum": self.minimum,
            "details": self.details or {},
        }


@dataclass
class RoutingConfidence:
    """
    Combined parse + validation confidence for routing decisions.

    Key insight: Route on min(parse, validation), not average.

    High validation + low parse = requires escalation (danger zone).
    Low validation + high parse = incomplete verification (needs more checks).
    Low both = already filtered out earlier.
    """
    parse: ParseConfidence
    validation: ValidationConfidence

    parse_validation_mismatch_threshold: float = 0.30

    details: Optional[Dict[str, Any]] = field(default_factory=dict)

    @property
    def combined(self) -> float:
        """Route on minimum of parse and validation."""
        return min(self.parse.combined, self.validation.combined)

    @property
    def parse_validation_gap(self) -> float:
        """Absolute difference between parse and validation confidence."""
        return abs(self.parse.combined - self.validation.combined)

    @property
    def requires_escalation(self) -> bool:
        """
        True if parse and validation are mismatched (danger zone).

        Indicates: we might be confidently solving the wrong problem,
        or confidently not verifying what we think we verified.
        """
        return self.parse_validation_gap > self.parse_validation_mismatch_threshold

    @property
    def low_parse_high_validation(self) -> bool:
        """Dangerous: confidently verifying the wrong thing."""
        return (self.parse.combined < 0.40 and
                self.validation.combined > 0.70 and
                self.parse_validation_gap > self.parse_validation_mismatch_threshold)

    @property
    def low_validation_high_parse(self) -> bool:
        """Incomplete: understood but not well verified."""
        return (self.parse.combined > 0.70 and
                self.validation.combined < 0.40 and
                self.parse_validation_gap > self.parse_validation_mismatch_threshold)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parse": self.parse.to_dict(),
            "validation": self.validation.to_dict(),
            "combined": self.combined,
            "parse_validation_gap": self.parse_validation_gap,
            "requires_escalation": self.requires_escalation,
            "low_parse_high_validation": self.low_parse_high_validation,
            "low_validation_high_parse": self.low_validation_high_parse,
            "details": self.details or {},
        }


# Helper functions for building confidence
def build_parse_confidence(
    syntax_score: float = 0.5,
    semantic_score: float = 0.5,
    completeness_score: float = 0.5,
    details: Optional[Dict[str, Any]] = None,
) -> ParseConfidence:
    """Factory for ParseConfidence."""
    return ParseConfidence(
        syntax_score=max(0.0, min(1.0, syntax_score)),
        semantic_score=max(0.0, min(1.0, semantic_score)),
        completeness_score=max(0.0, min(1.0, completeness_score)),
        details=details or {},
    )


def build_validation_confidence(
    symbolic_score: float = 0.5,
    numeric_score: float = 0.5,
    structural_score: float = 0.5,
    diversity_score: float = 0.5,
    details: Optional[Dict[str, Any]] = None,
) -> ValidationConfidence:
    """Factory for ValidationConfidence."""
    return ValidationConfidence(
        symbolic_score=max(0.0, min(1.0, symbolic_score)),
        numeric_score=max(0.0, min(1.0, numeric_score)),
        structural_score=max(0.0, min(1.0, structural_score)),
        diversity_score=max(0.0, min(1.0, diversity_score)),
        details=details or {},
    )


def build_routing_confidence(
    parse: ParseConfidence,
    validation: ValidationConfidence,
    details: Optional[Dict[str, Any]] = None,
) -> RoutingConfidence:
    """Factory for RoutingConfidence."""
    return RoutingConfidence(
        parse=parse,
        validation=validation,
        details=details or {},
    )
