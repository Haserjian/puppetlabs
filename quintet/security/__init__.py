"""
Quintet Security Module
=======================

Security hardening utilities for the Quintet orchestrator.

Components:
- Input sanitization (math expressions, paths)
- Resource limits (timeouts)

See SECURITY_THREAT_MODEL.md for threat analysis.
"""

from quintet.security.input_sanitizer import (
    # Math sanitization
    sanitize_math_expression,
    SanitizationResult,
    is_safe_math_expression,
    DANGEROUS_PATTERNS,
    
    # Path validation
    validate_path_within_root,
    PathValidationResult,
    validate_file_path,
    
    # Timeouts
    run_with_timeout,
    with_timeout,
    TimeoutError,
)

__all__ = [
    # Math
    "sanitize_math_expression",
    "SanitizationResult",
    "is_safe_math_expression",
    "DANGEROUS_PATTERNS",
    
    # Path
    "validate_path_within_root",
    "PathValidationResult",
    "validate_file_path",
    
    # Timeout
    "run_with_timeout",
    "with_timeout",
    "TimeoutError",
]
