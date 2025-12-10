"""
Test-time helpers
=================

This module is imported automatically by Python when present.
We use it to provide a couple of utility functions in the builtins
namespace so that test modules which reference `_sympy_available()`
and `_numpy_available()` before defining them do not crash with
NameError during import.

The test suite later defines its own versions of these helpers,
which will shadow the builtins; we only need them to exist early
enough for decorators like `@pytest.mark.skipif(not _sympy_available(), ...)`
to evaluate successfully.
"""

import builtins


def _sympy_available() -> bool:
    """Return True if SymPy can be imported."""
    try:
        import sympy  # type: ignore
        return True
    except Exception:
        return False


def _numpy_available() -> bool:
    """Return True if NumPy can be imported."""
    try:
        import numpy  # type: ignore
        return True
    except Exception:
        return False


# Expose helpers via builtins so unqualified references in tests work
if not hasattr(builtins, "_sympy_available"):
    builtins._sympy_available = _sympy_available

if not hasattr(builtins, "_numpy_available"):
    builtins._numpy_available = _numpy_available

