"""
Math Mode Robustness Utilities
===============================

Hardening utilities for multivariate math:
- Capability matrix for operations
- Solution normalizer for SymPy outputs
- Canonical variable ordering
- Tolerance-based verification helpers
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum


# =============================================================================
# CAPABILITY MATRIX
# =============================================================================

class MathCapability(Enum):
    """Capabilities that backends may or may not support."""
    # SymPy (Tier 1)
    SOLVE_SINGLE = "solve_single"           # Single equation, single variable
    SOLVE_SYSTEM = "solve_system"           # Multiple equations, multiple variables
    SIMPLIFY = "simplify"
    EXPAND = "expand"
    FACTOR = "factor"
    INTEGRATE = "integrate"
    DIFFERENTIATE = "differentiate"
    GRADIENT = "gradient"
    HESSIAN = "hessian"
    LIMIT = "limit"
    SERIES = "series"
    MATRIX_OPS = "matrix_ops"               # inv, det, eigenvalues
    
    # Numeric (Tier 1)
    NUMERIC_EVAL = "numeric_eval"
    LINEAR_SOLVE = "linear_solve"
    
    # SciPy-dependent (Tier 1+)
    ROOT_FIND = "root_find"
    MINIMIZE = "minimize"
    INTEGRATE_NUMERIC = "integrate_numeric"
    ODE = "ode"
    
    # Stats (Tier 2)
    OLS = "ols"
    GLM = "glm"
    IV_2SLS = "iv_2sls"
    PANEL = "panel"
    ARIMA = "arima"


@dataclass
class CapabilityInfo:
    """Info about a capability."""
    capability: MathCapability
    backend: str
    available: bool
    requires: List[str] = field(default_factory=list)  # Required packages
    notes: str = ""


# Backend capability registry
CAPABILITY_REGISTRY: Dict[str, Dict[MathCapability, CapabilityInfo]] = {}


def register_capability(
    backend: str,
    capability: MathCapability,
    available: bool,
    requires: List[str] = None,
    notes: str = ""
):
    """Register a backend's capability."""
    if backend not in CAPABILITY_REGISTRY:
        CAPABILITY_REGISTRY[backend] = {}
    
    CAPABILITY_REGISTRY[backend][capability] = CapabilityInfo(
        capability=capability,
        backend=backend,
        available=available,
        requires=requires or [],
        notes=notes
    )


def check_capability(backend: str, capability: MathCapability) -> Tuple[bool, str]:
    """
    Check if a backend supports a capability.
    
    Returns (available, reason).
    """
    if backend not in CAPABILITY_REGISTRY:
        return False, f"Unknown backend: {backend}"
    
    if capability not in CAPABILITY_REGISTRY[backend]:
        return False, f"Capability {capability.value} not registered for {backend}"
    
    info = CAPABILITY_REGISTRY[backend][capability]
    if not info.available:
        reason = f"Capability {capability.value} not available"
        if info.requires:
            reason += f"; requires: {', '.join(info.requires)}"
        if info.notes:
            reason += f"; {info.notes}"
        return False, reason
    
    return True, "OK"


def get_capable_backends(capability: MathCapability) -> List[str]:
    """Get list of backends that support a capability."""
    return [
        backend for backend, caps in CAPABILITY_REGISTRY.items()
        if capability in caps and caps[capability].available
    ]


# =============================================================================
# SOLUTION NORMALIZER
# =============================================================================

@dataclass
class NormalizedSolution:
    """
    Canonical representation of a solver output.
    
    All solution types (single, multiple, parametric) are normalized
    to a consistent shape.
    """
    # List of solution dicts, each mapping variable -> value
    solutions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Variable ordering used (for gradients/Hessians)
    variable_order: List[str] = field(default_factory=list)
    
    # Metadata
    is_unique: bool = True          # Single solution?
    is_parametric: bool = False     # Contains free parameters?
    free_parameters: List[str] = field(default_factory=list)
    branches: int = 1               # Number of solution branches
    
    # Raw output for debugging
    raw_output: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "solutions": self.solutions,
            "variable_order": self.variable_order,
            "is_unique": self.is_unique,
            "is_parametric": self.is_parametric,
            "free_parameters": self.free_parameters,
            "branches": self.branches
        }
    
    @property
    def primary_solution(self) -> Optional[Dict[str, Any]]:
        """Get the first/primary solution if available."""
        return self.solutions[0] if self.solutions else None


def normalize_sympy_solution(
    raw_output: Any,
    expected_variables: List[str] = None
) -> NormalizedSolution:
    """
    Normalize SymPy solve() output to canonical form.
    
    SymPy can return:
    - Single value: [3]
    - Multiple values: [-2, 2]
    - Dict: {x: 1, y: 2}
    - List of dicts: [{x: 1, y: 2}, {x: -1, y: -2}]
    - List of tuples: [(1, 2), (-1, -2)]
    - FiniteSet: FiniteSet(1, 2)
    - Piecewise or conditional
    """
    try:
        import sympy
        has_sympy = True
    except ImportError:
        has_sympy = False
    
    result = NormalizedSolution(raw_output=raw_output)
    
    if raw_output is None:
        return result
    
    # Determine variable order
    if expected_variables:
        result.variable_order = list(expected_variables)
    
    # Handle different SymPy return types
    if isinstance(raw_output, dict):
        # Single solution as dict: {x: 1, y: 2}
        sol = {str(k): _simplify_value(v) for k, v in raw_output.items()}
        if expected_variables:
            # Respect caller‑provided ordering
            ordered = {var: sol.get(var) for var in expected_variables if var in sol}
            sol = ordered
            result.variable_order = [var for var in expected_variables if var in sol]
        else:
            result.variable_order = list(sol.keys())
        result.solutions = [sol]
        result.is_unique = True
        result.branches = 1
        
    elif isinstance(raw_output, (list, tuple)):
        if not raw_output:
            return result
        
        first = raw_output[0]
        
        if isinstance(first, dict):
            # List of dicts: [{x: 1, y: 2}, ...]
            sols = [
                {str(k): _simplify_value(v) for k, v in sol.items()}
                for sol in raw_output
            ]
            if expected_variables and sols:
                # Reorder each solution dict according to expected variable order
                ordered_solutions: List[Dict[str, Any]] = []
                for sol in sols:
                    ordered = {var: sol.get(var) for var in expected_variables if var in sol}
                    ordered_solutions.append(ordered)
                result.solutions = ordered_solutions
                result.variable_order = [var for var in expected_variables if var in ordered_solutions[0]]
            else:
                result.solutions = sols
                if result.solutions:
                    result.variable_order = list(result.solutions[0].keys())
            result.is_unique = len(result.solutions) == 1
            result.branches = len(result.solutions)
            
        elif isinstance(first, (list, tuple)):
            # List of tuples: [(1, 2), (-1, -2)]
            if expected_variables and len(expected_variables) == len(first):
                result.solutions = [
                    {var: _simplify_value(val) for var, val in zip(expected_variables, sol)}
                    for sol in raw_output
                ]
                result.variable_order = list(expected_variables)
            else:
                # Fallback: use generic names
                result.solutions = [
                    {f"x{i}": _simplify_value(val) for i, val in enumerate(sol)}
                    for sol in raw_output
                ]
                result.variable_order = [f"x{i}" for i in range(len(first))]
            result.is_unique = len(result.solutions) == 1
            result.branches = len(result.solutions)
            
        else:
            # List of scalar values: [1, 2, 3]
            if expected_variables and len(expected_variables) == 1:
                var = expected_variables[0]
                result.solutions = [{var: _simplify_value(v)} for v in raw_output]
                result.variable_order = [var]
            else:
                result.solutions = [{"x": _simplify_value(v)} for v in raw_output]
                result.variable_order = ["x"]
            result.is_unique = len(result.solutions) == 1
            result.branches = len(result.solutions)
    
    elif has_sympy and isinstance(raw_output, sympy.FiniteSet):
        # FiniteSet: convert to list
        values = list(raw_output)
        if expected_variables and len(expected_variables) == 1:
            var = expected_variables[0]
            result.solutions = [{var: _simplify_value(v)} for v in values]
            result.variable_order = [var]
        else:
            result.solutions = [{"x": _simplify_value(v)} for v in values]
            result.variable_order = ["x"]
        result.is_unique = len(result.solutions) == 1
        result.branches = len(result.solutions)
    
    else:
        # Single scalar value
        if expected_variables and len(expected_variables) == 1:
            var = expected_variables[0]
            result.solutions = [{var: _simplify_value(raw_output)}]
            result.variable_order = [var]
        else:
            result.solutions = [{"x": _simplify_value(raw_output)}]
            result.variable_order = ["x"]
        result.is_unique = True
        result.branches = 1
    
    # Check for parametric solutions (free symbols in values)
    if has_sympy:
        for sol in result.solutions:
            for val in sol.values():
                if hasattr(val, 'free_symbols') and val.free_symbols:
                    result.is_parametric = True
                    for sym in val.free_symbols:
                        param = str(sym)
                        if param not in result.free_parameters:
                            result.free_parameters.append(param)
    
    return result


def _simplify_value(val: Any) -> Any:
    """Simplify a value for storage, keeping it serializable where possible."""
    try:
        import sympy
        if isinstance(val, sympy.Basic):
            # Try to convert to Python number if possible
            if val.is_number:
                # Prefer real-valued floats/ints where possible so that
                # downstream callers (and tests) can safely cast with
                # float(...) without tripping over complex types.
                try:
                    if getattr(val, "is_real", False):
                        return float(val)
                    # Fallback: complex for genuinely complex numbers
                    return complex(val)
                except Exception:
                    try:
                        return float(val)
                    except Exception:
                        return str(val)
            return val  # Keep as sympy for further processing
    except ImportError:
        pass
    return val


# =============================================================================
# CANONICAL VARIABLE ORDERING
# =============================================================================

def canonical_variable_order(variables: List[str]) -> List[str]:
    """
    Return a canonical ordering of variable names.
    
    Ordering rules:
    1. Single letters before multi-letter (x before xy)
    2. Alphabetical within groups
    3. Subscripted versions after base (x before x1, x1 before x2)
    """
    def sort_key(v: str) -> Tuple[int, str, int]:
        # Extract base and numeric suffix
        import re
        match = re.match(r'^([a-zA-Z_]+)(\d*)$', v)
        if match:
            base = match.group(1)
            suffix = int(match.group(2)) if match.group(2) else 0
        else:
            base = v
            suffix = 0
        
        # Length priority (shorter first)
        length_priority = len(base)
        
        return (length_priority, base.lower(), suffix)
    
    return sorted(variables, key=sort_key)


# =============================================================================
# TOLERANCE-BASED VERIFICATION
# =============================================================================

@dataclass
class ToleranceConfig:
    """Configuration for tolerance-based checks."""
    absolute: float = 1e-9      # Absolute tolerance
    relative: float = 1e-6      # Relative tolerance
    max_magnitude: float = 1e12  # Maximum reasonable value
    
    def is_zero(self, value: float) -> bool:
        """Check if a value is effectively zero."""
        return abs(value) < self.absolute
    
    def is_close(self, a: float, b: float) -> bool:
        """Check if two values are close."""
        if abs(a) < self.absolute and abs(b) < self.absolute:
            return True
        return abs(a - b) <= self.absolute + self.relative * max(abs(a), abs(b))


DEFAULT_TOLERANCE = ToleranceConfig()


def substitution_check_with_tolerance(
    expression: Any,
    solution: Dict[str, Any],
    tolerance: ToleranceConfig = None
) -> Tuple[bool, float, str]:
    """
    Check if substituting solution into expression gives zero (with tolerance).
    
    Returns: (passed, residual, message)
    """
    tolerance = tolerance or DEFAULT_TOLERANCE
    
    try:
        import sympy
    except ImportError:
        return False, float('inf'), "SymPy not available"
    
    try:
        # Convert expression if string
        if isinstance(expression, str):
            expr = sympy.sympify(expression)
        else:
            expr = expression
        
        # Build substitution dict with sympy symbols
        subs = {}
        for var, val in solution.items():
            sym = sympy.Symbol(var)
            subs[sym] = val
        
        # Substitute
        result = expr.subs(subs)
        
        # Try to evaluate numerically
        try:
            numeric_result = complex(result.evalf())
            residual = abs(numeric_result)
            
            if tolerance.is_zero(residual):
                return True, residual, f"Substitution verified (residual={residual:.2e})"
            else:
                return False, residual, f"Residual too large: {residual:.2e}"
        except:
            # Can't evaluate numerically - try symbolic simplification
            simplified = sympy.simplify(result)
            if simplified == 0:
                return True, 0.0, "Symbolically verified (simplifies to 0)"
            else:
                return False, float('inf'), f"Does not simplify to 0: {simplified}"
    
    except Exception as e:
        return False, float('inf'), f"Substitution error: {e}"


def finite_difference_gradient_check(
    gradient_symbolic: List[Any],
    expression: Any,
    variables: List[str],
    point: Dict[str, float],
    h: float = 1e-7,
    tolerance: ToleranceConfig = None
) -> Tuple[bool, List[Tuple[float, float]], str]:
    """
    Verify symbolic gradient against finite differences.
    
    Returns: (passed, list of (symbolic, numeric) pairs, message)
    """
    tolerance = tolerance or DEFAULT_TOLERANCE
    
    try:
        import sympy
        import numpy as np
    except ImportError:
        return False, [], "SymPy or NumPy not available"
    
    try:
        # Convert expression if string
        if isinstance(expression, str):
            expr = sympy.sympify(expression)
        else:
            expr = expression
        
        # Build symbol dict
        symbols = {v: sympy.Symbol(v) for v in variables}
        
        # Evaluate expression at point
        def eval_at(pt: Dict[str, float]) -> float:
            subs = {symbols[v]: val for v, val in pt.items()}
            return float(expr.subs(subs).evalf())
        
        f_at_point = eval_at(point)
        
        # Check each gradient component
        comparisons = []
        all_passed = True
        
        for i, (var, grad_expr) in enumerate(zip(variables, gradient_symbolic)):
            # Symbolic gradient at point
            if isinstance(grad_expr, str):
                grad_expr = sympy.sympify(grad_expr)
            subs = {symbols[v]: val for v, val in point.items()}
            symbolic_val = float(grad_expr.subs(subs).evalf())
            
            # Finite difference
            pt_plus = point.copy()
            pt_plus[var] = point[var] + h
            pt_minus = point.copy()
            pt_minus[var] = point[var] - h
            
            numeric_val = (eval_at(pt_plus) - eval_at(pt_minus)) / (2 * h)
            
            comparisons.append((symbolic_val, numeric_val))
            
            if not tolerance.is_close(symbolic_val, numeric_val):
                all_passed = False
        
        if all_passed:
            return True, comparisons, "Gradient verified by finite differences"
        else:
            max_diff = max(abs(s - n) for s, n in comparisons)
            return False, comparisons, f"Gradient mismatch (max diff: {max_diff:.2e})"
    
    except Exception as e:
        return False, [], f"Finite difference check error: {e}"


# =============================================================================
# SIZE-AWARE ROUTING
# =============================================================================

@dataclass
class ProblemComplexity:
    """Estimated complexity of a math problem."""
    num_equations: int = 1
    num_variables: int = 1
    max_degree: int = 1
    is_linear: bool = True
    is_sparse: bool = False
    estimated_symbolic_cost: str = "low"  # "low" | "medium" | "high" | "extreme"
    recommended_path: str = "symbolic"    # "symbolic" | "numeric" | "hybrid"
    
    def should_prefer_numeric(self) -> bool:
        """Should we prefer numeric over symbolic?"""
        return (
            self.num_equations > 10 or
            self.num_variables > 10 or
            self.max_degree > 5 or
            self.estimated_symbolic_cost in ["high", "extreme"]
        )


def estimate_complexity(
    expressions: List[str],
    variables: List[str]
) -> ProblemComplexity:
    """Estimate the complexity of a math problem."""
    complexity = ProblemComplexity(
        num_equations=len(expressions),
        num_variables=len(variables)
    )
    
    try:
        import sympy
        
        # Analyze each expression
        max_degree = 0
        total_terms = 0
        
        for expr_str in expressions:
            try:
                expr = sympy.sympify(expr_str.replace("=", "-").replace("^", "**"))
                
                # Estimate degree
                for var in variables:
                    sym = sympy.Symbol(var)
                    try:
                        deg = sympy.degree(expr, sym)
                        max_degree = max(max_degree, deg)
                    except:
                        pass
                
                # Count terms
                if hasattr(expr, 'as_ordered_terms'):
                    total_terms += len(expr.as_ordered_terms())
            except:
                pass
        
        complexity.max_degree = max_degree
        # Ensure we store a plain Python bool, not a SymPy Boolean
        complexity.is_linear = bool(max_degree <= 1)
        
        # Estimate symbolic cost
        if complexity.num_equations <= 3 and complexity.num_variables <= 3:
            if complexity.max_degree <= 2:
                complexity.estimated_symbolic_cost = "low"
            elif complexity.max_degree <= 4:
                complexity.estimated_symbolic_cost = "medium"
            else:
                complexity.estimated_symbolic_cost = "high"
        elif complexity.num_equations <= 10:
            complexity.estimated_symbolic_cost = "medium" if complexity.is_linear else "high"
        else:
            complexity.estimated_symbolic_cost = "high" if complexity.is_linear else "extreme"
        
        # Recommend path
        if complexity.should_prefer_numeric():
            complexity.recommended_path = "numeric" if complexity.is_linear else "hybrid"
        else:
            complexity.recommended_path = "symbolic"
    
    except ImportError:
        pass
    
    return complexity

