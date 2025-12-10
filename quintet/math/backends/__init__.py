"""
Math Mode Backends
===================

Tier 1 (Required):
- SymPyBackend: Symbolic computation
- NumericBackend: Numerical computation (NumPy/SciPy)

Tier 2 (Optional):
- OptimizationBackend: CVXPY for convex optimization
- StatsBackend: statsmodels for statistical tests
- MLBackend: sklearn for traditional ML
- DeepBackend: PyTorch/JAX for deep learning
- PDEBackend: FEniCS/Firedrake for PDEs
- FormalBackend: Lean for formal proofs
- WolframBackend: Wolfram Alpha for fallback
"""

from quintet.math.backends.base import MathBackend, BackendResult
from quintet.math.backends.sympy_backend import SymPyBackend
from quintet.math.backends.numeric_backend import NumericBackend

__all__ = [
    "MathBackend",
    "BackendResult",
    "SymPyBackend",
    "NumericBackend",
]


