"""
Tests for Math Mode robustness utilities.

Tests:
- Capability registration and checking
- Solution normalization
- Canonical variable ordering
- Tolerance-based verification
- Finite-difference gradient checks
- Complexity estimation
"""

import pytest
from typing import Dict, Any


# =============================================================================
# CAPABILITY MATRIX TESTS
# =============================================================================

class TestCapabilityMatrix:
    """Tests for capability registration and checking."""
    
    def test_register_and_check_capability(self):
        """Test registering and checking a capability."""
        from quintet.math.robustness import (
            MathCapability, register_capability, check_capability,
            CAPABILITY_REGISTRY
        )
        
        # Register a test capability
        register_capability(
            "test_backend",
            MathCapability.SOLVE_SINGLE,
            True,
            ["test_package"]
        )
        
        # Check it
        available, reason = check_capability("test_backend", MathCapability.SOLVE_SINGLE)
        assert available is True
        assert reason == "OK"
    
    def test_check_unavailable_capability(self):
        """Test checking an unavailable capability."""
        from quintet.math.robustness import (
            MathCapability, register_capability, check_capability
        )
        
        # Register unavailable capability
        register_capability(
            "test_backend2",
            MathCapability.ROOT_FIND,
            False,
            ["scipy"],
            notes="Requires SciPy"
        )
        
        available, reason = check_capability("test_backend2", MathCapability.ROOT_FIND)
        assert available is False
        assert "not available" in reason
        assert "scipy" in reason.lower()
    
    def test_get_capable_backends(self):
        """Test getting backends that support a capability."""
        from quintet.math.robustness import (
            MathCapability, register_capability, get_capable_backends
        )
        
        # Register multiple backends with same capability
        register_capability("backend_a", MathCapability.SIMPLIFY, True)
        register_capability("backend_b", MathCapability.SIMPLIFY, True)
        register_capability("backend_c", MathCapability.SIMPLIFY, False)
        
        capable = get_capable_backends(MathCapability.SIMPLIFY)
        assert "backend_a" in capable
        assert "backend_b" in capable
        assert "backend_c" not in capable


# =============================================================================
# SOLUTION NORMALIZER TESTS
# =============================================================================

class TestSolutionNormalizer:
    """Tests for SymPy solution normalization."""
    
    def test_normalize_single_dict(self):
        """Test normalizing a single dict solution."""
        from quintet.math.robustness import normalize_sympy_solution
        
        raw = {"x": 3, "y": 5}
        result = normalize_sympy_solution(raw, ["x", "y"])
        
        assert len(result.solutions) == 1
        assert result.solutions[0]["x"] == 3
        assert result.solutions[0]["y"] == 5
        assert result.is_unique is True
        assert result.branches == 1
    
    def test_normalize_list_of_dicts(self):
        """Test normalizing multiple solutions as list of dicts."""
        from quintet.math.robustness import normalize_sympy_solution
        
        raw = [{"x": 1, "y": 2}, {"x": -1, "y": -2}]
        result = normalize_sympy_solution(raw, ["x", "y"])
        
        assert len(result.solutions) == 2
        assert result.is_unique is False
        assert result.branches == 2
    
    def test_normalize_scalar_list(self):
        """Test normalizing scalar solution list."""
        from quintet.math.robustness import normalize_sympy_solution
        
        raw = [2, -2]
        result = normalize_sympy_solution(raw, ["x"])
        
        assert len(result.solutions) == 2
        assert result.solutions[0]["x"] == 2
        assert result.solutions[1]["x"] == -2
    
    def test_normalize_preserves_variable_order(self):
        """Test that variable ordering is preserved."""
        from quintet.math.robustness import normalize_sympy_solution
        
        raw = {"y": 10, "x": 5}
        result = normalize_sympy_solution(raw, ["x", "y"])
        
        assert result.variable_order[0] == "x"
        assert result.variable_order[1] == "y"


# =============================================================================
# CANONICAL VARIABLE ORDERING TESTS
# =============================================================================

class TestCanonicalVariableOrder:
    """Tests for canonical variable ordering."""
    
    def test_single_letters_first(self):
        """Test that single letters come before multi-letter names."""
        from quintet.math.robustness import canonical_variable_order
        
        result = canonical_variable_order(["xy", "x", "abc", "y"])
        assert result[0] == "x"
        assert result[1] == "y"
        assert "xy" in result[2:]
        assert "abc" in result[2:]
    
    def test_alphabetical_within_groups(self):
        """Test alphabetical ordering within groups."""
        from quintet.math.robustness import canonical_variable_order
        
        result = canonical_variable_order(["z", "a", "m"])
        assert result == ["a", "m", "z"]
    
    def test_numeric_suffixes(self):
        """Test ordering with numeric suffixes."""
        from quintet.math.robustness import canonical_variable_order
        
        result = canonical_variable_order(["x2", "x", "x1", "x10"])
        assert result[0] == "x"
        assert result[1] == "x1"
        assert result[2] == "x2"
        assert result[3] == "x10"


# =============================================================================
# TOLERANCE-BASED VERIFICATION TESTS
# =============================================================================

class TestToleranceVerification:
    """Tests for tolerance-based verification."""
    
    def test_tolerance_config_is_zero(self):
        """Test is_zero with tolerance."""
        from quintet.math.robustness import ToleranceConfig
        
        config = ToleranceConfig(absolute=1e-9)
        
        assert config.is_zero(0.0) is True
        assert config.is_zero(1e-10) is True
        assert config.is_zero(1e-8) is False
    
    def test_tolerance_config_is_close(self):
        """Test is_close with tolerance."""
        from quintet.math.robustness import ToleranceConfig
        
        config = ToleranceConfig(absolute=1e-9, relative=1e-6)
        
        assert config.is_close(1.0, 1.0 + 1e-10) is True
        assert config.is_close(1.0, 1.0001) is False
    
    @pytest.mark.skipif(
        not _sympy_available(),
        reason="SymPy not installed"
    )
    def test_substitution_check_passes(self):
        """Test substitution check with valid solution."""
        from quintet.math.robustness import substitution_check_with_tolerance
        
        # x^2 - 4 = 0, solution x=2
        passed, residual, msg = substitution_check_with_tolerance(
            "x**2 - 4",
            {"x": 2}
        )
        
        assert passed is True
        assert residual < 1e-9
    
    @pytest.mark.skipif(
        not _sympy_available(),
        reason="SymPy not installed"
    )
    def test_substitution_check_fails(self):
        """Test substitution check with invalid solution."""
        from quintet.math.robustness import substitution_check_with_tolerance
        
        # x^2 - 4 = 0, wrong solution x=3
        passed, residual, msg = substitution_check_with_tolerance(
            "x**2 - 4",
            {"x": 3}
        )
        
        assert passed is False
        assert residual > 1


# =============================================================================
# FINITE DIFFERENCE GRADIENT TESTS
# =============================================================================

class TestFiniteDifferenceGradient:
    """Tests for finite-difference gradient verification."""
    
    @pytest.mark.skipif(
        not (_sympy_available() and _numpy_available()),
        reason="SymPy and NumPy required"
    )
    def test_gradient_check_passes(self):
        """Test gradient check with correct gradient."""
        from quintet.math.robustness import finite_difference_gradient_check
        import sympy
        
        # f(x, y) = x^2 + y^2
        # gradient = [2*x, 2*y]
        x, y = sympy.symbols('x y')
        gradient = [2*x, 2*y]
        
        passed, comparisons, msg = finite_difference_gradient_check(
            gradient,
            "x**2 + y**2",
            ["x", "y"],
            {"x": 1.0, "y": 1.0}
        )
        
        assert passed is True
        assert len(comparisons) == 2
    
    @pytest.mark.skipif(
        not (_sympy_available() and _numpy_available()),
        reason="SymPy and NumPy required"
    )
    def test_gradient_check_fails_wrong_gradient(self):
        """Test gradient check with incorrect gradient."""
        from quintet.math.robustness import finite_difference_gradient_check
        import sympy
        
        # f(x, y) = x^2 + y^2
        # Wrong gradient = [x, y] (should be [2*x, 2*y])
        x, y = sympy.symbols('x y')
        wrong_gradient = [x, y]
        
        passed, comparisons, msg = finite_difference_gradient_check(
            wrong_gradient,
            "x**2 + y**2",
            ["x", "y"],
            {"x": 1.0, "y": 1.0}
        )
        
        assert passed is False


# =============================================================================
# COMPLEXITY ESTIMATION TESTS
# =============================================================================

class TestComplexityEstimation:
    """Tests for problem complexity estimation."""
    
    @pytest.mark.skipif(
        not _sympy_available(),
        reason="SymPy not installed"
    )
    def test_simple_linear_system(self):
        """Test complexity estimation for simple linear system."""
        from quintet.math.robustness import estimate_complexity
        
        complexity = estimate_complexity(
            ["x + y - 5", "2*x - y - 1"],
            ["x", "y"]
        )
        
        assert complexity.num_equations == 2
        assert complexity.num_variables == 2
        assert complexity.is_linear is True
        assert complexity.estimated_symbolic_cost == "low"
        assert complexity.should_prefer_numeric() is False
    
    @pytest.mark.skipif(
        not _sympy_available(),
        reason="SymPy not installed"
    )
    def test_large_system_prefers_numeric(self):
        """Test that large systems prefer numeric path."""
        from quintet.math.robustness import estimate_complexity
        
        # Create a 15-variable system
        expressions = [f"x{i} + x{i+1} - {i}" for i in range(15)]
        variables = [f"x{i}" for i in range(16)]
        
        complexity = estimate_complexity(expressions, variables)
        
        assert complexity.num_equations == 15
        assert complexity.num_variables == 16
        assert complexity.should_prefer_numeric() is True


# =============================================================================
# INTEGRATION TESTS (WITH SYMPY BACKEND)
# =============================================================================

class TestBackendIntegration:
    """Integration tests with SymPy backend using robustness utilities."""
    
    @pytest.mark.skipif(
        not _sympy_available(),
        reason="SymPy not installed"
    )
    def test_sympy_solve_with_normalization(self):
        """Test that SymPy solve can be normalized."""
        from quintet.math.backends.sympy_backend import SymPyBackend
        from quintet.math.robustness import normalize_sympy_solution
        
        backend = SymPyBackend()
        result = backend.execute(
            "solve",
            {"expressions": ["x + y - 5", "x - y - 1"], "variables": ["x", "y"]}
        )
        
        assert result.success is True
        
        # Normalize the result
        normalized = normalize_sympy_solution(result.output, ["x", "y"])
        assert len(normalized.solutions) >= 1
        
        # Check solution
        sol = normalized.primary_solution
        assert sol is not None
    
    @pytest.mark.skipif(
        not _sympy_available(),
        reason="SymPy not installed"
    )
    def test_gradient_with_canonical_ordering(self):
        """Test that gradient uses canonical variable ordering."""
        from quintet.math.backends.sympy_backend import SymPyBackend
        
        backend = SymPyBackend()
        
        # Variables should be ordered: x, y (alphabetically)
        result = backend.execute(
            "gradient",
            {"expression": "y**2 + x**2", "variables": ["y", "x"]}
        )
        
        assert result.success is True
        # After canonical ordering, x comes before y
        # So gradient should be [d/dx, d/dy] = [2*x, 2*y]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _sympy_available() -> bool:
    """Check if SymPy is available."""
    try:
        import sympy
        return True
    except ImportError:
        return False


def _numpy_available() -> bool:
    """Check if NumPy is available."""
    try:
        import numpy
        return True
    except ImportError:
        return False


