"""
Input Sanitizer for Quintet
===========================

Targeted security hardening for:
1. Math expression sanitization (prevent sympify ACE)
2. Path validation (prevent path traversal)
3. Resource limits (timeouts for long-running operations)

Threat Model Reference: SECURITY_THREAT_MODEL.md
"""

import re
import signal
from pathlib import Path
from typing import Optional, Tuple, List, Any, Callable, TypeVar
from dataclasses import dataclass
from functools import wraps

T = TypeVar('T')


# =============================================================================
# MATH EXPRESSION SANITIZATION (P1: Critical)
# =============================================================================

@dataclass
class SanitizationResult:
    """Result of input sanitization."""
    safe: bool
    sanitized_input: str
    original_input: str
    warnings: List[str]
    blocked_patterns: List[str]

    def to_dict(self):
        return {
            "safe": self.safe,
            "sanitized_input": self.sanitized_input,
            "original_input": self.original_input,
            "warnings": self.warnings,
            "blocked_patterns": self.blocked_patterns,
        }


# Patterns that could enable code execution via sympify
# sympify() can execute arbitrary Python if given certain patterns
DANGEROUS_PATTERNS = [
    # Direct code execution
    (r'__\w+__', 'dunder methods'),           # __import__, __builtins__, etc.
    (r'\beval\s*\(', 'eval() call'),
    (r'\bexec\s*\(', 'exec() call'),
    (r'\bcompile\s*\(', 'compile() call'),
    (r'\bopen\s*\(', 'open() call'),
    (r'\bimport\s+', 'import statement'),
    (r'\bfrom\s+\w+\s+import', 'from import'),
    
    # Object attribute access that could reach builtins
    (r'\.__class__', '__class__ access'),
    (r'\.__bases__', '__bases__ access'),
    (r'\.__mro__', '__mro__ access'),
    (r'\.__subclasses__', '__subclasses__ access'),
    (r'\.__globals__', '__globals__ access'),
    (r'\.__code__', '__code__ access'),
    
    # Lambda/function definition
    (r'\blambda\s*:', 'lambda expression'),
    (r'\bdef\s+\w+', 'function definition'),
    
    # System access
    (r'\bos\s*\.', 'os module access'),
    (r'\bsys\s*\.', 'sys module access'),
    (r'\bsubprocess', 'subprocess module'),
    (r'\bshutil', 'shutil module'),
    
    # SymPy-specific dangerous patterns
    (r'S\s*\(\s*[\'"]', 'SymPy S() with string'),
    (r'sympify\s*\(', 'direct sympify call'),
]

# Allowed characters for math expressions
# Letters, numbers, and safe math operators
SAFE_MATH_CHARS = re.compile(r'^[\w\s+\-*/^()=<>.,\[\]{}|&!]+$')


def sanitize_math_expression(expr: str) -> SanitizationResult:
    """
    Sanitize a math expression before passing to sympify.
    
    This is a defense-in-depth measure. Even though sympify has some
    protections, we add an extra layer for:
    1. Detecting obvious code injection attempts
    2. Logging suspicious patterns
    3. Providing clear error messages
    
    Args:
        expr: Raw expression string
        
    Returns:
        SanitizationResult with safe=True if expression is safe to parse
    """
    if not expr or not isinstance(expr, str):
        return SanitizationResult(
            safe=True,
            sanitized_input="",
            original_input=str(expr) if expr else "",
            warnings=[],
            blocked_patterns=[]
        )
    
    warnings = []
    blocked = []
    
    # Check for dangerous patterns
    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, expr, re.IGNORECASE):
            blocked.append(f"{description} detected")
    
    if blocked:
        return SanitizationResult(
            safe=False,
            sanitized_input="",
            original_input=expr,
            warnings=[f"Expression blocked due to: {', '.join(blocked)}"],
            blocked_patterns=blocked
        )
    
    # Warn about unusual characters but allow if no dangerous patterns
    if not SAFE_MATH_CHARS.match(expr):
        unusual = set(c for c in expr if not re.match(r'[\w\s+\-*/^()=<>.,\[\]{}|&!]', c))
        warnings.append(f"Unusual characters detected: {unusual}")
    
    # Basic length check - extremely long expressions are suspicious
    if len(expr) > 10000:
        warnings.append(f"Expression unusually long: {len(expr)} chars")
    
    return SanitizationResult(
        safe=True,
        sanitized_input=expr,
        original_input=expr,
        warnings=warnings,
        blocked_patterns=[]
    )


# =============================================================================
# PATH VALIDATION (P3: Medium)
# =============================================================================

@dataclass
class PathValidationResult:
    """Result of path validation."""
    valid: bool
    resolved_path: Optional[Path]
    error: Optional[str]


def validate_path_within_root(
    path: str,
    root: Path,
    allow_absolute: bool = False
) -> PathValidationResult:
    """
    Validate that a path stays within the project root.
    
    Prevents path traversal attacks like:
    - ../../../etc/passwd
    - /etc/passwd (absolute paths)
    - symlink escapes
    
    Args:
        path: Path to validate (relative or absolute)
        root: Project root directory
        allow_absolute: Whether to allow absolute paths
        
    Returns:
        PathValidationResult with valid=True if path is safe
    """
    if not path:
        return PathValidationResult(
            valid=False,
            resolved_path=None,
            error="Empty path"
        )
    
    try:
        # Convert to Path objects
        root = Path(root).resolve()
        target = Path(path)
        
        # Check for absolute paths
        if target.is_absolute() and not allow_absolute:
            return PathValidationResult(
                valid=False,
                resolved_path=None,
                error=f"Absolute paths not allowed: {path}"
            )
        
        # Resolve the full path (handles .., symlinks, etc.)
        if target.is_absolute():
            resolved = target.resolve()
        else:
            resolved = (root / target).resolve()
        
        # Check if resolved path is within root
        try:
            resolved.relative_to(root)
            return PathValidationResult(
                valid=True,
                resolved_path=resolved,
                error=None
            )
        except ValueError:
            return PathValidationResult(
                valid=False,
                resolved_path=None,
                error=f"Path escapes project root: {path} -> {resolved}"
            )
            
    except Exception as e:
        return PathValidationResult(
            valid=False,
            resolved_path=None,
            error=f"Path validation error: {str(e)}"
        )


# =============================================================================
# RESOURCE LIMITS / TIMEOUTS (P2: High)
# =============================================================================

class TimeoutError(Exception):
    """Raised when an operation times out."""
    pass


def _timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutError("Operation timed out")


def with_timeout(timeout_seconds: float = 30.0):
    """
    Decorator that adds a timeout to a function.
    
    Uses SIGALRM on Unix systems. Falls back to no timeout on Windows.
    
    Args:
        timeout_seconds: Maximum execution time in seconds
        
    Returns:
        Decorated function that raises TimeoutError if it takes too long
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Try to use signal-based timeout (Unix only)
            if hasattr(signal, 'SIGALRM'):
                old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
                signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
                try:
                    return func(*args, **kwargs)
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    signal.signal(signal.SIGALRM, old_handler)
            else:
                # No signal support (Windows) - run without timeout
                return func(*args, **kwargs)
        return wrapper
    return decorator


def run_with_timeout(
    func: Callable[..., T],
    args: tuple = (),
    kwargs: dict = None,
    timeout_seconds: float = 30.0,
    default: T = None
) -> Tuple[bool, T, Optional[str]]:
    """
    Run a function with a timeout.
    
    Args:
        func: Function to run
        args: Positional arguments
        kwargs: Keyword arguments
        timeout_seconds: Maximum execution time
        default: Default value to return on timeout
        
    Returns:
        Tuple of (success, result, error_message)
    """
    kwargs = kwargs or {}
    
    @with_timeout(timeout_seconds)
    def run():
        return func(*args, **kwargs)
    
    try:
        result = run()
        return (True, result, None)
    except TimeoutError:
        return (False, default, f"Operation timed out after {timeout_seconds}s")
    except Exception as e:
        return (False, default, str(e))


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def is_safe_math_expression(expr: str) -> bool:
    """Quick check if expression is safe for sympify."""
    return sanitize_math_expression(expr).safe


def validate_file_path(path: str, project_root: str) -> bool:
    """Quick check if file path is safe."""
    return validate_path_within_root(path, Path(project_root)).valid
