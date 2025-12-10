"""
Tests for ParseConfidence vs ValidationConfidence splitting.
"""

import pytest
from quintet.core.confidence import (
    ParseConfidence, ValidationConfidence, RoutingConfidence,
    build_parse_confidence, build_validation_confidence, build_routing_confidence,
)


class TestParseConfidence:
    """Parse confidence: understanding the problem."""

    def test_parse_confidence_creation(self):
        """Create parse confidence."""
        pc = ParseConfidence(syntax_score=0.9, semantic_score=0.8, completeness_score=0.7)
        assert pc.syntax_score == 0.9
        assert pc.semantic_score == 0.8
        assert pc.completeness_score == 0.7

    def test_parse_confidence_combined(self):
        """Combined parse confidence is average."""
        pc = ParseConfidence(syntax_score=0.9, semantic_score=0.6, completeness_score=0.3)
        expected = (0.9 + 0.6 + 0.3) / 3
        assert pc.combined == pytest.approx(expected)

    def test_parse_confidence_minimum_bottleneck(self):
        """Minimum is bottleneck component."""
        pc = ParseConfidence(syntax_score=0.9, semantic_score=0.5, completeness_score=0.7)
        assert pc.minimum == 0.5

    def test_parse_confidence_serialization(self):
        """Parse confidence to_dict."""
        pc = ParseConfidence(syntax_score=0.8, semantic_score=0.6, completeness_score=0.7)
        d = pc.to_dict()
        assert d["syntax_score"] == 0.8
        assert d["semantic_score"] == 0.6
        assert d["completeness_score"] == 0.7
        assert "combined" in d


class TestValidationConfidence:
    """Validation confidence: solution correctness."""

    def test_validation_confidence_creation(self):
        """Create validation confidence."""
        vc = ValidationConfidence(symbolic_score=0.9, numeric_score=0.8,
                                 structural_score=0.7, diversity_score=0.6)
        assert vc.symbolic_score == 0.9
        assert vc.numeric_score == 0.8

    def test_validation_confidence_combined(self):
        """Combined validation confidence is average."""
        vc = ValidationConfidence(symbolic_score=0.8, numeric_score=0.8,
                                 structural_score=0.8, diversity_score=0.8)
        assert vc.combined == pytest.approx(0.8)

    def test_validation_confidence_minimum(self):
        """Minimum is bottleneck."""
        vc = ValidationConfidence(symbolic_score=0.9, numeric_score=0.3,
                                 structural_score=0.9, diversity_score=0.9)
        assert vc.minimum == 0.3


class TestRoutingConfidence:
    """Routing confidence: combined parse + validation."""

    def test_routing_confidence_both_high(self):
        """Both high: safe to route normally."""
        pc = build_parse_confidence(syntax_score=0.9, semantic_score=0.9, completeness_score=0.9)
        vc = build_validation_confidence(symbolic_score=0.9, numeric_score=0.9,
                                        structural_score=0.9, diversity_score=0.9)
        rc = build_routing_confidence(pc, vc)

        assert rc.combined == pytest.approx(0.9)
        assert not rc.requires_escalation

    def test_routing_confidence_uses_minimum(self):
        """Routing uses min(parse, validation)."""
        pc = build_parse_confidence(syntax_score=0.8, semantic_score=0.8, completeness_score=0.8)
        vc = build_validation_confidence(symbolic_score=0.5, numeric_score=0.5,
                                        structural_score=0.5, diversity_score=0.5)
        rc = build_routing_confidence(pc, vc)

        assert rc.combined == pytest.approx(0.5)

    def test_danger_zone_low_parse_high_validation(self):
        """Danger: high validation but low parse confidence."""
        pc = build_parse_confidence(syntax_score=0.2, semantic_score=0.2, completeness_score=0.2)
        vc = build_validation_confidence(symbolic_score=0.9, numeric_score=0.9,
                                        structural_score=0.9, diversity_score=0.9)
        rc = build_routing_confidence(pc, vc)

        assert rc.low_parse_high_validation
        assert rc.requires_escalation

    def test_incomplete_low_validation_high_parse(self):
        """Incomplete: high parse but low validation."""
        pc = build_parse_confidence(syntax_score=0.9, semantic_score=0.9, completeness_score=0.9)
        vc = build_validation_confidence(symbolic_score=0.2, numeric_score=0.2,
                                        structural_score=0.2, diversity_score=0.2)
        rc = build_routing_confidence(pc, vc)

        assert rc.low_validation_high_parse
        assert rc.requires_escalation

    def test_small_gap_no_escalation(self):
        """Small parse/validation gap: no escalation needed."""
        pc = build_parse_confidence(syntax_score=0.7, semantic_score=0.7, completeness_score=0.7)
        vc = build_validation_confidence(symbolic_score=0.65, numeric_score=0.65,
                                        structural_score=0.65, diversity_score=0.65)
        rc = build_routing_confidence(pc, vc)

        assert rc.parse_validation_gap < 0.30
        assert not rc.requires_escalation

    def test_gap_exceeds_threshold(self):
        """Gap exceeds mismatch threshold."""
        pc = build_parse_confidence(syntax_score=0.9, semantic_score=0.9, completeness_score=0.9)
        vc = build_validation_confidence(symbolic_score=0.5, numeric_score=0.5,
                                        structural_score=0.5, diversity_score=0.5)
        rc = build_routing_confidence(pc, vc)

        assert rc.parse_validation_gap > 0.30
        assert rc.requires_escalation
