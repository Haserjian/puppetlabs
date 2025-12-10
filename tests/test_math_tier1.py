"""
Math Mode Tier 1 Tests
=======================

Tests for the core Math Mode functionality (Tier 1).
Requires: sympy, numpy

Run: pytest tests/test_math_tier1.py -v
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def math_mode():
    """Create a Math Mode orchestrator."""
    from quintet.math import create_math_mode
    return create_math_mode()


@pytest.fixture
def detector():
    """Create a Math Detector."""
    from quintet.math.detector import MathDetector
    return MathDetector()


# =============================================================================
# DETECTOR TESTS
# =============================================================================

class TestMathDetector:
    """Tests for MathDetector."""
    
    def test_detect_algebra(self, detector):
        """Test detection of algebra problems."""
        intent = detector.detect("Solve x^2 - 4 = 0")
        assert intent.is_math
        assert intent.domain.value == "algebra"
        assert intent.problem_type == "solve"
        assert intent.confidence > 0.5
    
    def test_detect_calculus(self, detector):
        """Test detection of calculus problems."""
        intent = detector.detect("Integrate x^2 dx")
        assert intent.is_math
        assert intent.domain.value == "calculus"
        assert intent.problem_type == "integrate"
    
    def test_detect_linear_algebra(self, detector):
        """Test detection of linear algebra problems."""
        intent = detector.detect("Find the eigenvalues of matrix A")
        assert intent.is_math
        assert intent.domain.value == "linear_algebra"
    
    def test_detect_not_math(self, detector):
        """Test detection of non-math queries."""
        intent = detector.detect("Build a web app with React")
        assert not intent.is_math or intent.confidence < 0.3


# =============================================================================
# PARSER TESTS
# =============================================================================

class TestProblemParser:
    """Tests for ProblemParser."""
    
    def test_parse_equation(self, detector):
        """Test parsing an equation."""
        from quintet.math.parser import ProblemParser
        parser = ProblemParser()
        
        intent = detector.detect("Solve x^2 - 4 = 0")
        problem = parser.parse("Solve x^2 - 4 = 0", intent)
        
        assert problem.parsed_successfully
        assert "x" in problem.variables
        assert problem.goal == "x"
    
    def test_parse_expression(self, detector):
        """Test parsing a simple expression."""
        from quintet.math.parser import ProblemParser
        parser = ProblemParser()
        
        intent = detector.detect("Simplify (x + 1)^2")
        problem = parser.parse("Simplify (x + 1)^2", intent)
        
        assert problem.parsed_successfully


# =============================================================================
# BACKEND TESTS
# =============================================================================

class TestSymPyBackend:
    """Tests for SymPy backend."""
    
    @pytest.fixture
    def backend(self):
        from quintet.math.backends import SymPyBackend
        return SymPyBackend()
    
    def test_availability(self, backend):
        """Test that SymPy is available."""
        assert backend.is_available
    
    def test_solve_quadratic(self, backend):
        """Test solving a quadratic equation."""
        result = backend.execute("solve", {
            "expression": "x**2 - 4",
            "variable": "x"
        })
        
        assert result.success
        assert -2 in result.output or result.output == [-2, 2]
        assert 2 in result.output or result.output == [-2, 2]
    
    def test_integrate(self, backend):
        """Test integration."""
        result = backend.execute("integrate", {
            "expression": "x**2",
            "variable": "x"
        })
        
        assert result.success
        assert "x**3/3" in str(result.output) or "x³/3" in str(result.output)
    
    def test_differentiate(self, backend):
        """Test differentiation."""
        result = backend.execute("differentiate", {
            "expression": "x**3",
            "variable": "x"
        })
        
        assert result.success
        assert "3*x**2" in str(result.output) or "3x²" in str(result.output)


class TestNumericBackend:
    """Tests for NumPy/SciPy backend."""
    
    @pytest.fixture
    def backend(self):
        from quintet.math.backends import NumericBackend
        return NumericBackend()
    
    def test_availability(self, backend):
        """Test that NumPy is available."""
        assert backend.is_available
    
    def test_linear_solve(self, backend):
        """Test solving linear system."""
        result = backend.execute("linear_solve", {
            "A": [[2, 1], [1, 3]],
            "b": [4, 5]
        })
        
        assert result.success
        # Solution should be approximately [1.4, 1.2]


# =============================================================================
# ORCHESTRATOR TESTS
# =============================================================================

class TestMathModeOrchestrator:
    """Tests for the full Math Mode orchestrator."""
    
    def test_solve_simple_equation(self, math_mode):
        """Test solving a simple equation end-to-end."""
        result = math_mode.process("Solve x^2 - 9 = 0")
        
        assert result.success
        assert result.intent.is_math
        assert result.result is not None
        # Solutions should be -3 and 3
        answer = result.result.final_answer
        assert -3 in answer or 3 in answer
    
    def test_integration(self, math_mode):
        """Test integration end-to-end."""
        result = math_mode.process("Integrate 2*x with respect to x")
        
        assert result.success
        assert result.intent.domain.value == "calculus"
        assert "x**2" in str(result.result.final_answer)
    
    def test_validation_included(self, math_mode):
        """Test that validation is performed."""
        result = math_mode.process("Solve 2x + 4 = 10")
        
        assert result.success
        assert result.validation is not None
        assert result.validation.confidence > 0
    
    def test_color_tiles_generated(self, math_mode):
        """Test that color tiles are generated."""
        result = math_mode.process("Factor x^2 - 1")
        
        assert result.color_tiles is not None
        assert len(result.color_tiles.tiles) == 9  # 3x3 grid
    
    def test_context_flow_populated(self, math_mode):
        """Test that context flow is recorded."""
        result = math_mode.process("Simplify (x+1)(x-1)")
        
        assert len(result.context_flow) > 0
        phases = [cf.phase for cf in result.context_flow]
        assert "observe" in phases
        assert "orient" in phases or "act" in phases

    def test_solve_system_two_variables(self, math_mode):
        """Solve a 2x2 system of equations."""
        result = math_mode.process("Solve x + y = 5 and 2x - y = 1")
        assert result.success
        sol = result.result.final_answer
        # SymPy may return a list of dicts or dict
        if isinstance(sol, list):
            sol = sol[0]
        assert float(sol.get('x')) == 2.0
        assert float(sol.get('y')) == 3.0

    def test_gradient_multivariate(self, math_mode):
        """Compute gradient of a multivariate function."""
        result = math_mode.process("Find the gradient of x^2 + y^2 + x*y")
        assert result.success
        grad = result.result.final_answer
        # Gradient can come back as list of sympy expressions
        assert len(grad) == 2
        grad_strs = [str(g) for g in grad]
        assert "2*x + y" in grad_strs or "y + 2*x" in grad_strs
        assert "2*y + x" in grad_strs or "x + 2*y" in grad_strs


# =============================================================================
# CORE TYPES TESTS
# =============================================================================

class TestCoreTypes:
    """Tests for core shared types."""
    
    def test_validation_result_properties(self):
        """Test ValidationResult computed properties."""
        from quintet.core import ValidationCheck, ValidationResult
        
        checks = [
            ValidationCheck("check1", "core", True, 0.3, "passed"),
            ValidationCheck("check2", "core", False, 0.2, "failed"),
            ValidationCheck("check3", "domain", True, 0.2, "passed"),
        ]
        
        result = ValidationResult(
            valid=True,
            confidence=0.5,
            checks=checks
        )
        
        assert result.checks_passed == 2
        assert result.checks_failed == 1
    
    def test_color_tile_grid_to_dict(self):
        """Test ColorTileGrid serialization."""
        from quintet.core import ColorTile, ColorTileGrid
        
        tiles = [
            ColorTile("A1", "#4CAF50", "confident", "success", "Test Tile")
        ]
        
        grid = ColorTileGrid(
            grid_id="test-grid",
            mode="math",
            tiles=tiles
        )
        
        d = grid.to_dict()
        assert d["grid_id"] == "test-grid"
        assert d["mode"] == "math"
        assert len(d["tiles"]) == 1
    
    def test_incompleteness_assessment_gating(self):
        """Test IncompletenessAssessment auto-gating."""
        from quintet.core import IncompletenessAssessment
        
        # Low score should disable auto-approve
        assessment = IncompletenessAssessment(score=0.4)
        assert not assessment.auto_approve_allowed
        assert len(assessment.next_steps) > 0
        
        # High score should allow auto-approve
        assessment = IncompletenessAssessment(score=0.9)
        assert assessment.auto_approve_allowed


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

