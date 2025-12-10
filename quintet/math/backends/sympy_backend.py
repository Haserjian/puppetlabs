"""
SymPy Backend (Tier 1 Required)
================================

Symbolic mathematics using SymPy.
Handles: algebra, calculus, linear algebra, basic probability.
"""

import time
from typing import Any, Dict, Optional, List, Tuple

from quintet.math.backends.base import MathBackend, BackendResult
from quintet.math.robustness import (
    MathCapability, register_capability,
    normalize_sympy_solution, NormalizedSolution,
    canonical_variable_order
)


class SymPyBackend(MathBackend):
    """
    SymPy-based symbolic computation backend.
    
    This is the primary Tier 1 backend - required for Math Mode.
    """
    
    def __init__(self):
        self._sympy = None
        self._available = False
        self._init_sympy()
        self._register_capabilities()
    
    def _init_sympy(self):
        """Try to import sympy."""
        try:
            import sympy
            self._sympy = sympy
            self._available = True
        except ImportError:
            self._available = False
    
    def _register_capabilities(self):
        """Register this backend's capabilities."""
        available = self._available
        register_capability("sympy", MathCapability.SOLVE_SINGLE, available, ["sympy"])
        register_capability("sympy", MathCapability.SOLVE_SYSTEM, available, ["sympy"])
        register_capability("sympy", MathCapability.SIMPLIFY, available, ["sympy"])
        register_capability("sympy", MathCapability.EXPAND, available, ["sympy"])
        register_capability("sympy", MathCapability.FACTOR, available, ["sympy"])
        register_capability("sympy", MathCapability.INTEGRATE, available, ["sympy"])
        register_capability("sympy", MathCapability.DIFFERENTIATE, available, ["sympy"])
        register_capability("sympy", MathCapability.GRADIENT, available, ["sympy"])
        register_capability("sympy", MathCapability.HESSIAN, available, ["sympy"])
        register_capability("sympy", MathCapability.LIMIT, available, ["sympy"])
        register_capability("sympy", MathCapability.SERIES, available, ["sympy"])
        register_capability("sympy", MathCapability.MATRIX_OPS, available, ["sympy"])
    
    @property
    def name(self) -> str:
        return "sympy"
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    @property
    def capabilities(self) -> List[str]:
        return [
            "symbolic",
            "solve",
            "gradient",
            "hessian",
            "simplify",
            "expand",
            "factor",
            "integrate",
            "differentiate",
            "limit",
            "series",
            "matrix",
            "eigenvalues",
            "determinant",
            "inverse",
            "probability",
        ]
    
    def execute(
        self,
        operation: str,
        inputs: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> BackendResult:
        """Execute a symbolic computation."""
        if not self._available:
            return BackendResult(
                success=False,
                output=None,
                errors=["SymPy not available. Install with: pip install sympy"]
            )
        
        options = options or {}
        start = time.time()
        
        try:
            result = self._dispatch(operation, inputs, options)
            elapsed = (time.time() - start) * 1000
            
            # Generate LaTeX
            latex_output = None
            if result is not None:
                try:
                    latex_output = self._sympy.latex(result)
                except:
                    pass
            
            return BackendResult(
                success=True,
                output=result,
                output_latex=latex_output,
                method_used=f"sympy.{operation}",
                execution_time_ms=elapsed
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return BackendResult(
                success=False,
                output=None,
                method_used=f"sympy.{operation}",
                execution_time_ms=elapsed,
                errors=[str(e)]
            )
    
    def _dispatch(
        self, 
        operation: str, 
        inputs: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Any:
        """Dispatch to appropriate SymPy function."""
        
        if operation == "solve":
            return self._solve(inputs, options)
        elif operation == "simplify":
            return self._simplify(inputs)
        elif operation == "expand":
            return self._expand(inputs)
        elif operation == "factor":
            return self._factor(inputs)
        elif operation == "integrate":
            return self._integrate(inputs, options)
        elif operation == "differentiate":
            return self._differentiate(inputs, options)
        elif operation == "limit":
            return self._limit(inputs, options)
        elif operation == "series":
            return self._series(inputs, options)
        elif operation == "matrix_inverse":
            return self._matrix_inverse(inputs)
        elif operation == "determinant":
            return self._determinant(inputs)
        elif operation == "eigenvalues":
            return self._eigenvalues(inputs)
        elif operation == "gradient":
            return self._gradient(inputs)
        elif operation == "hessian":
            return self._hessian(inputs)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    def _sympify_equation(self, expr: Any):
        """Parse equation strings to sympy expressions; handle lhs = rhs."""
        if not isinstance(expr, str):
            return expr
        if "=" in expr and "==" not in expr:
            parts = expr.split("=")
            if len(parts) == 2:
                lhs = self._sympy.sympify(parts[0].strip())
                rhs = self._sympy.sympify(parts[1].strip())
                return lhs - rhs
        return self._sympy.sympify(expr)
    
    def _solve(self, inputs: Dict[str, Any], options: Dict[str, Any]) -> Any:
        """
        Solve equations.

        Returns raw SymPy output. For single‑equation / single‑variable
        problems we delegate to SymPy with scalar arguments so that the
        result is a flat list like ``[-2, 2]`` instead of
        ``[(-2,), (2,)]``.  For genuine systems we pass the usual
        ``(equations, variables)`` pair so callers can normalize as
        needed.
        """
        expr = inputs.get("expression")
        exprs = inputs.get("expressions")
        variable = inputs.get("variable")
        variables = inputs.get("variables")
        
        if expr is None and not exprs:
            raise ValueError("No expression provided to solve")
        
        # Normalize expressions into a list
        if exprs:
            to_solve = []
            for item in exprs:
                to_solve.append(self._sympify_equation(item))
        else:
            to_solve = [self._sympify_equation(expr)]
        
        # Build symbols with canonical ordering
        if variables:
            var_names = canonical_variable_order(list(variables))
            var_symbols = [self._sympy.Symbol(v) for v in var_names]
        elif variable:
            var_symbols = [self._sympy.Symbol(variable)]
        else:
            # Attempt to infer symbols from expression with canonical ordering
            all_symbols = {sym for ex in to_solve for sym in ex.free_symbols}
            var_names = canonical_variable_order([str(s) for s in all_symbols])
            var_symbols = [self._sympy.Symbol(v) for v in var_names]

        # Heuristic: scalar equation vs system
        is_system = len(to_solve) > 1 or len(var_symbols) > 1

        if not is_system:
            # Single equation, single variable: ask SymPy for a flat list
            raw_result = self._sympy.solve(to_solve[0], var_symbols[0])
        else:
            # System: let SymPy handle the full vector form
            # (callers can normalize to dicts via normalize_sympy_solution)
            raw_result = self._sympy.solve(to_solve, var_symbols)
        
        # Optionally normalize if requested
        if options.get("normalize", False):
            expected_vars = [str(s) for s in var_symbols]
            return normalize_sympy_solution(raw_result, expected_vars)
        
        return raw_result
    
    def _simplify(self, inputs: Dict[str, Any]) -> Any:
        """Simplify expression."""
        expr = inputs.get("expression")
        if isinstance(expr, str):
            expr = self._sympy.sympify(expr)
        return self._sympy.simplify(expr)
    
    def _expand(self, inputs: Dict[str, Any]) -> Any:
        """Expand expression."""
        expr = inputs.get("expression")
        if isinstance(expr, str):
            expr = self._sympy.sympify(expr)
        return self._sympy.expand(expr)
    
    def _factor(self, inputs: Dict[str, Any]) -> Any:
        """Factor expression."""
        expr = inputs.get("expression")
        if isinstance(expr, str):
            expr = self._sympy.sympify(expr)
        return self._sympy.factor(expr)
    
    def _integrate(self, inputs: Dict[str, Any], options: Dict[str, Any]) -> Any:
        """Integrate expression."""
        expr = inputs.get("expression")
        variable = inputs.get("variable", "x")
        bounds = inputs.get("bounds")  # (lower, upper) for definite
        
        if isinstance(expr, str):
            expr = self._sympy.sympify(expr)
        
        var = self._sympy.Symbol(variable)
        
        if bounds:
            return self._sympy.integrate(expr, (var, bounds[0], bounds[1]))
        else:
            return self._sympy.integrate(expr, var)
    
    def _differentiate(self, inputs: Dict[str, Any], options: Dict[str, Any]) -> Any:
        """Differentiate expression."""
        expr = inputs.get("expression")
        variable = inputs.get("variable", "x")
        order = inputs.get("order", 1)
        
        if isinstance(expr, str):
            expr = self._sympy.sympify(expr)
        
        var = self._sympy.Symbol(variable)
        return self._sympy.diff(expr, var, order)
    
    def _limit(self, inputs: Dict[str, Any], options: Dict[str, Any]) -> Any:
        """Compute limit."""
        expr = inputs.get("expression")
        variable = inputs.get("variable", "x")
        point = inputs.get("point", 0)
        direction = inputs.get("direction", "+")
        
        if isinstance(expr, str):
            expr = self._sympy.sympify(expr)
        
        var = self._sympy.Symbol(variable)
        return self._sympy.limit(expr, var, point, direction)
    
    def _series(self, inputs: Dict[str, Any], options: Dict[str, Any]) -> Any:
        """Taylor/Maclaurin series expansion."""
        expr = inputs.get("expression")
        variable = inputs.get("variable", "x")
        point = inputs.get("point", 0)
        order = inputs.get("order", 6)
        
        if isinstance(expr, str):
            expr = self._sympy.sympify(expr)
        
        var = self._sympy.Symbol(variable)
        return self._sympy.series(expr, var, point, order)
    
    def _matrix_inverse(self, inputs: Dict[str, Any]) -> Any:
        """Compute matrix inverse."""
        matrix = inputs.get("matrix")
        if isinstance(matrix, list):
            matrix = self._sympy.Matrix(matrix)
        return matrix.inv()
    
    def _determinant(self, inputs: Dict[str, Any]) -> Any:
        """Compute determinant."""
        matrix = inputs.get("matrix")
        if isinstance(matrix, list):
            matrix = self._sympy.Matrix(matrix)
        return matrix.det()
    
    def _eigenvalues(self, inputs: Dict[str, Any]) -> Any:
        """Compute eigenvalues."""
        matrix = inputs.get("matrix")
        if isinstance(matrix, list):
            matrix = self._sympy.Matrix(matrix)
        return matrix.eigenvals()

    def _gradient(self, inputs: Dict[str, Any]) -> Any:
        """
        Compute gradient of an expression with respect to variables.
        
        Uses canonical variable ordering for consistency.
        Returns: List of partial derivatives in variable order.
        """
        expr = inputs.get("expression")
        variables = inputs.get("variables") or []
        if isinstance(expr, str):
            expr = self._sympy.sympify(expr)
        if not variables:
            # Use canonical ordering for consistency
            variables = canonical_variable_order([str(v) for v in expr.free_symbols])
        else:
            variables = canonical_variable_order(list(variables))
        symbols = [self._sympy.Symbol(v) for v in variables]
        gradient = [self._sympy.diff(expr, v) for v in symbols]
        
        # Include variable ordering metadata in result for downstream
        # Note: The result is a list; metadata is available via the inputs
        return gradient

    def _hessian(self, inputs: Dict[str, Any]) -> Any:
        """
        Compute Hessian matrix.
        
        Uses canonical variable ordering for consistency.
        Returns: SymPy Matrix of second partial derivatives.
        """
        expr = inputs.get("expression")
        variables = inputs.get("variables") or []
        if isinstance(expr, str):
            expr = self._sympy.sympify(expr)
        if not variables:
            # Use canonical ordering for consistency
            variables = canonical_variable_order([str(v) for v in expr.free_symbols])
        else:
            variables = canonical_variable_order(list(variables))
        symbols = [self._sympy.Symbol(v) for v in variables]
        return self._sympy.hessian(expr, symbols)
