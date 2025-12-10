"""
Numeric Backend (Tier 1 Required)
==================================

Numerical computation using NumPy and SciPy.
Handles: numerical evaluation, root finding, optimization, linear algebra.

Capability-aware: Operations requiring SciPy are gated and will fail fast
with a clear error if SciPy is not installed.
"""

import time
from typing import Any, Dict, Optional, List, Tuple

from quintet.math.backends.base import MathBackend, BackendResult
from quintet.math.robustness import (
    MathCapability, register_capability, check_capability
)


class NumericBackend(MathBackend):
    """
    NumPy/SciPy-based numerical computation backend.
    
    Complements SymPy for numerical verification and computation.
    
    Capability-gated: SciPy-dependent operations explicitly check for
    availability and fail fast with clear errors.
    """
    
    def __init__(self):
        self._numpy = None
        self._scipy = None
        self._numpy_available = False
        self._scipy_available = False
        self._init_backends()
        self._register_capabilities()
    
    def _init_backends(self):
        """Try to import numpy and scipy."""
        try:
            import numpy
            self._numpy = numpy
            self._numpy_available = True
        except ImportError:
            pass
        
        try:
            import scipy
            from scipy import optimize, linalg
            self._scipy = scipy
            self._scipy_optimize = optimize
            self._scipy_linalg = linalg
            self._scipy_available = True
        except ImportError:
            pass
    
    def _register_capabilities(self):
        """Register this backend's capabilities."""
        # NumPy-only capabilities
        register_capability(
            "numeric", MathCapability.NUMERIC_EVAL, 
            self._numpy_available, ["numpy"]
        )
        register_capability(
            "numeric", MathCapability.LINEAR_SOLVE,
            self._numpy_available, ["numpy"],
            notes="Uses numpy.linalg.solve"
        )
        
        # SciPy-dependent capabilities
        register_capability(
            "numeric", MathCapability.ROOT_FIND,
            self._scipy_available, ["numpy", "scipy"],
            notes="Requires scipy.optimize"
        )
        register_capability(
            "numeric", MathCapability.MINIMIZE,
            self._scipy_available, ["numpy", "scipy"],
            notes="Requires scipy.optimize"
        )
        register_capability(
            "numeric", MathCapability.INTEGRATE_NUMERIC,
            self._scipy_available, ["numpy", "scipy"],
            notes="Requires scipy.integrate"
        )
        register_capability(
            "numeric", MathCapability.ODE,
            self._scipy_available, ["numpy", "scipy"],
            notes="Requires scipy.integrate"
        )
    
    @property
    def name(self) -> str:
        return "numeric"
    
    @property
    def is_available(self) -> bool:
        return self._numpy_available
    
    @property
    def scipy_available(self) -> bool:
        """Check if SciPy is available for advanced operations."""
        return self._scipy_available
    
    @property
    def capabilities(self) -> List[str]:
        caps = ["numeric", "evaluate"]
        if self._numpy_available:
            caps.extend(["array", "matrix_numeric", "linear_solve", "dot", "norm",
                        "eigenvalues_numeric", "determinant_numeric", "inverse_numeric"])
        if self._scipy_available:
            caps.extend(["root_find", "minimize", "integrate_numeric", "ode"])
        return caps
    
    # Operations that require SciPy
    SCIPY_REQUIRED_OPS = {"root_find", "minimize", "integrate_numeric", "ode"}
    
    def supports(self, operation: str) -> bool:
        """Check if this backend supports an operation."""
        if operation in self.SCIPY_REQUIRED_OPS:
            return self._scipy_available
        return operation in self.capabilities
    
    def execute(
        self,
        operation: str,
        inputs: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> BackendResult:
        """Execute a numerical computation."""
        if not self._numpy_available:
            return BackendResult(
                success=False,
                output=None,
                errors=["NumPy not available. Install with: pip install numpy"]
            )
        
        options = options or {}
        start = time.time()
        
        try:
            result = self._dispatch(operation, inputs, options)
            elapsed = (time.time() - start) * 1000
            
            # Format output for display
            output_str = None
            if hasattr(result, '__iter__') and not isinstance(result, str):
                output_str = str(result)
            
            return BackendResult(
                success=True,
                output=result,
                output_latex=output_str,
                method_used=f"numeric.{operation}",
                execution_time_ms=elapsed
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return BackendResult(
                success=False,
                output=None,
                method_used=f"numeric.{operation}",
                execution_time_ms=elapsed,
                errors=[str(e)]
            )
    
    def _dispatch(
        self,
        operation: str,
        inputs: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Any:
        """
        Dispatch to appropriate function.
        
        Explicitly checks capability before executing SciPy-dependent operations.
        """
        # Gate SciPy-dependent operations
        if operation in self.SCIPY_REQUIRED_OPS:
            if not self._scipy_available:
                raise RuntimeError(
                    f"Operation '{operation}' requires SciPy. "
                    f"Install with: pip install scipy"
                )
        
        if operation == "evaluate":
            return self._evaluate(inputs)
        elif operation == "linear_solve":
            return self._linear_solve(inputs)
        elif operation == "root_find":
            return self._root_find(inputs, options)
        elif operation == "minimize":
            return self._minimize(inputs, options)
        elif operation == "integrate_numeric":
            return self._integrate_numeric(inputs, options)
        elif operation == "matrix_multiply":
            return self._matrix_multiply(inputs)
        elif operation == "eigenvalues_numeric":
            return self._eigenvalues_numeric(inputs)
        elif operation == "determinant_numeric":
            return self._determinant_numeric(inputs)
        elif operation == "inverse_numeric":
            return self._inverse_numeric(inputs)
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def _evaluate(self, inputs: Dict[str, Any]) -> Any:
        """Evaluate expression at given values."""
        func = inputs.get("function")
        values = inputs.get("values", {})
        
        if callable(func):
            return func(**values)
        
        # If string expression, try to evaluate with numpy
        if isinstance(func, str):
            # Create namespace with numpy functions
            namespace = {
                "sin": self._numpy.sin,
                "cos": self._numpy.cos,
                "tan": self._numpy.tan,
                "exp": self._numpy.exp,
                "log": self._numpy.log,
                "sqrt": self._numpy.sqrt,
                "pi": self._numpy.pi,
                "e": self._numpy.e,
            }
            namespace.update(values)
            return eval(func, {"__builtins__": {}}, namespace)
        
        return None
    
    def _linear_solve(self, inputs: Dict[str, Any]) -> Any:
        """Solve Ax = b."""
        A = self._numpy.array(inputs.get("A"))
        b = self._numpy.array(inputs.get("b"))
        return self._numpy.linalg.solve(A, b)
    
    def _root_find(self, inputs: Dict[str, Any], options: Dict[str, Any]) -> Any:
        """Find root of function."""
        if not self._scipy_available:
            raise RuntimeError("SciPy required for root finding")
        
        func = inputs.get("function")
        x0 = inputs.get("x0", 0)
        method = options.get("method", "brentq")
        
        if method == "brentq" and "bounds" in inputs:
            bounds = inputs["bounds"]
            return self._scipy_optimize.brentq(func, bounds[0], bounds[1])
        else:
            return self._scipy_optimize.fsolve(func, x0)
    
    def _minimize(self, inputs: Dict[str, Any], options: Dict[str, Any]) -> Any:
        """Minimize function."""
        if not self._scipy_available:
            raise RuntimeError("SciPy required for optimization")
        
        func = inputs.get("function")
        x0 = inputs.get("x0")
        method = options.get("method", "BFGS")
        bounds = inputs.get("bounds")
        constraints = inputs.get("constraints")
        
        result = self._scipy_optimize.minimize(
            func, x0, 
            method=method,
            bounds=bounds,
            constraints=constraints
        )
        return {
            "x": result.x.tolist() if hasattr(result.x, 'tolist') else result.x,
            "fun": float(result.fun),
            "success": result.success,
            "message": result.message
        }
    
    def _integrate_numeric(self, inputs: Dict[str, Any], options: Dict[str, Any]) -> Any:
        """Numerical integration."""
        if not self._scipy_available:
            raise RuntimeError("SciPy required for numerical integration")
        
        from scipy import integrate
        
        func = inputs.get("function")
        bounds = inputs.get("bounds")
        
        result, error = integrate.quad(func, bounds[0], bounds[1])
        return {"value": result, "error": error}
    
    def _matrix_multiply(self, inputs: Dict[str, Any]) -> Any:
        """Matrix multiplication."""
        A = self._numpy.array(inputs.get("A"))
        B = self._numpy.array(inputs.get("B"))
        return self._numpy.matmul(A, B)
    
    def _eigenvalues_numeric(self, inputs: Dict[str, Any]) -> Any:
        """Compute eigenvalues numerically."""
        matrix = self._numpy.array(inputs.get("matrix"))
        eigenvalues, eigenvectors = self._numpy.linalg.eig(matrix)
        return {
            "eigenvalues": eigenvalues.tolist(),
            "eigenvectors": eigenvectors.tolist()
        }
    
    def _determinant_numeric(self, inputs: Dict[str, Any]) -> Any:
        """Compute determinant numerically."""
        matrix = self._numpy.array(inputs.get("matrix"))
        return float(self._numpy.linalg.det(matrix))
    
    def _inverse_numeric(self, inputs: Dict[str, Any]) -> Any:
        """Compute matrix inverse numerically."""
        matrix = self._numpy.array(inputs.get("matrix"))
        return self._numpy.linalg.inv(matrix).tolist()

