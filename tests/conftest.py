"""
Pytest configuration for shared helpers.

Some test modules (e.g. tests/test_robustness.py) reference helper
functions `_sympy_available()` and `_numpy_available()` in decorators
before defining them. That causes a NameError at import time unless
those names exist in the global/builtins scope early.

We provide simple implementations here and register them in `builtins`
so that the decorators can evaluate safely. The test modules later
define their own versions, which will shadow these; our only goal is
to avoid failing during collection.
"""

import builtins


def _sympy_available() -> bool:
    try:
        import sympy  # type: ignore
        return True
    except Exception:
        return False


def _numpy_available() -> bool:
    try:
        import numpy  # type: ignore
        return True
    except Exception:
        return False


if not hasattr(builtins, "_sympy_available"):
    builtins._sympy_available = _sympy_available

if not hasattr(builtins, "_numpy_available"):
    builtins._numpy_available = _numpy_available

