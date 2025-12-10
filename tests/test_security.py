"""
Tests for Security Hardening (Phase 2)
======================================

Tests for:
1. Math expression sanitization (P1: Critical)
2. Path validation (P3: Medium)
3. Resource limits/timeouts (P2: High)

Threat Model Reference: SECURITY_THREAT_MODEL.md
"""

import pytest
import time
import tempfile
from pathlib import Path

from quintet.security.input_sanitizer import (
    sanitize_math_expression,
    SanitizationResult,
    validate_path_within_root,
    PathValidationResult,
    run_with_timeout,
    with_timeout,
    TimeoutError,
    is_safe_math_expression,
    validate_file_path,
    DANGEROUS_PATTERNS,
)


# =============================================================================
# MATH EXPRESSION SANITIZATION TESTS (P1)
# =============================================================================

class TestMathExpressionSanitization:
    """Tests for math expression sanitization."""
    
    def test_safe_simple_expression(self):
        """Test that simple math expressions pass."""
        result = sanitize_math_expression("x**2 + 2*x + 1")
        assert result.safe is True
        assert result.sanitized_input == "x**2 + 2*x + 1"
        assert len(result.blocked_patterns) == 0
    
    def test_safe_equation(self):
        """Test that equations pass."""
        result = sanitize_math_expression("x + y = 5")
        assert result.safe is True
    
    def test_safe_complex_expression(self):
        """Test complex but safe expressions."""
        expressions = [
            "sin(x) + cos(y)",
            "sqrt(x**2 + y**2)",
            "exp(-x**2/2)",
            "log(x) + ln(y)",
            "x**2 - 4 = 0",
            "3*x + 2*y - z = 10",
        ]
        for expr in expressions:
            result = sanitize_math_expression(expr)
            assert result.safe is True, f"Should be safe: {expr}"
    
    def test_block_dunder_import(self):
        """Test blocking __import__."""
        result = sanitize_math_expression("__import__('os')")
        assert result.safe is False
        assert len(result.blocked_patterns) > 0
    
    def test_block_eval(self):
        """Test blocking eval()."""
        result = sanitize_math_expression("eval('os.system(\"ls\")')")
        assert result.safe is False
        assert any("eval" in p.lower() for p in result.blocked_patterns)
    
    def test_block_exec(self):
        """Test blocking exec()."""
        result = sanitize_math_expression("exec('print(1)')")
        assert result.safe is False
        assert any("exec" in p.lower() for p in result.blocked_patterns)
    
    def test_block_open(self):
        """Test blocking open()."""
        result = sanitize_math_expression("open('/etc/passwd')")
        assert result.safe is False
        assert any("open" in p.lower() for p in result.blocked_patterns)
    
    def test_block_import_statement(self):
        """Test blocking import statements."""
        result = sanitize_math_expression("import os; x = 1")
        assert result.safe is False
        assert any("import" in p.lower() for p in result.blocked_patterns)
    
    def test_block_from_import(self):
        """Test blocking from...import."""
        result = sanitize_math_expression("from os import system")
        assert result.safe is False
        # Could be blocked by either "import" or "from import" pattern
        assert any("import" in p.lower() for p in result.blocked_patterns)
    
    def test_block_class_access(self):
        """Test blocking __class__ access."""
        result = sanitize_math_expression("().__class__.__bases__[0]")
        assert result.safe is False
        # Should be blocked for dunder or class access
        assert len(result.blocked_patterns) > 0
    
    def test_block_lambda(self):
        """Test blocking lambda expressions."""
        result = sanitize_math_expression("(lambda: __import__('os'))()")
        assert result.safe is False
        # Should be blocked for multiple reasons
        assert len(result.blocked_patterns) >= 1
    
    def test_block_os_module(self):
        """Test blocking os module access."""
        result = sanitize_math_expression("os.system('ls')")
        assert result.safe is False
        assert any("os" in p.lower() for p in result.blocked_patterns)
    
    def test_block_subprocess(self):
        """Test blocking subprocess module."""
        result = sanitize_math_expression("subprocess.run(['ls'])")
        assert result.safe is False
        assert any("subprocess" in p.lower() for p in result.blocked_patterns)
    
    def test_block_globals_access(self):
        """Test blocking __globals__ access."""
        result = sanitize_math_expression("f.__globals__['os']")
        assert result.safe is False
        # Can be blocked by dunder pattern or globals pattern
        assert len(result.blocked_patterns) > 0
    
    def test_empty_expression(self):
        """Test that empty expressions are safe (no-op)."""
        result = sanitize_math_expression("")
        assert result.safe is True
        
    def test_none_expression(self):
        """Test that None is handled safely."""
        result = sanitize_math_expression(None)
        assert result.safe is True
    
    def test_warn_unusual_characters(self):
        """Test warnings for unusual characters."""
        result = sanitize_math_expression("x + y; print('hi')")
        # Should pass (no dangerous patterns) but warn
        assert result.safe is True or "print" in str(result.blocked_patterns)
    
    def test_quick_check_function(self):
        """Test the quick check convenience function."""
        assert is_safe_math_expression("x**2 + 1") is True
        assert is_safe_math_expression("__import__('os')") is False


# =============================================================================
# PATH VALIDATION TESTS (P3)
# =============================================================================

class TestPathValidation:
    """Tests for path traversal prevention."""
    
    def test_valid_relative_path(self):
        """Test that relative paths within root are valid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = validate_path_within_root("subdir/file.txt", root)
            assert result.valid is True
            assert result.resolved_path is not None
    
    def test_valid_nested_path(self):
        """Test deeply nested paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = validate_path_within_root("a/b/c/d/file.txt", root)
            assert result.valid is True
    
    def test_block_parent_traversal(self):
        """Test blocking ../ traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = validate_path_within_root("../outside.txt", root)
            assert result.valid is False
            assert "escapes project root" in result.error
    
    def test_block_deep_traversal(self):
        """Test blocking deep ../ traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = validate_path_within_root("subdir/../../outside.txt", root)
            assert result.valid is False
    
    def test_block_etc_passwd(self):
        """Test blocking classic /etc/passwd attack."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = validate_path_within_root("../../../etc/passwd", root)
            assert result.valid is False
    
    def test_block_absolute_path_default(self):
        """Test blocking absolute paths by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = validate_path_within_root("/etc/passwd", root)
            assert result.valid is False
            assert "Absolute paths not allowed" in result.error
    
    def test_allow_absolute_when_enabled(self):
        """Test allowing absolute paths when explicitly enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            # Create a file inside the root with absolute path
            test_file = root / "test.txt"
            test_file.write_text("test")
            
            result = validate_path_within_root(
                str(test_file),
                root,
                allow_absolute=True
            )
            assert result.valid is True
    
    def test_block_absolute_outside_root(self):
        """Test blocking absolute paths outside root even when allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = validate_path_within_root(
                "/etc/passwd",
                root,
                allow_absolute=True
            )
            assert result.valid is False
            assert "escapes project root" in result.error
    
    def test_empty_path(self):
        """Test that empty paths are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = validate_path_within_root("", root)
            assert result.valid is False
            assert "Empty path" in result.error
    
    def test_quick_check_function(self):
        """Test the quick check convenience function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert validate_file_path("subdir/file.txt", tmpdir) is True
            assert validate_file_path("../outside.txt", tmpdir) is False


# =============================================================================
# TIMEOUT TESTS (P2)
# =============================================================================

class TestTimeouts:
    """Tests for timeout functionality."""
    
    def test_fast_function_succeeds(self):
        """Test that fast functions complete normally."""
        def fast():
            return 42
        
        success, result, error = run_with_timeout(fast, timeout_seconds=1.0)
        assert success is True
        assert result == 42
        assert error is None
    
    def test_slow_function_times_out(self):
        """Test that slow functions timeout."""
        def slow():
            time.sleep(5)
            return 42
        
        success, result, error = run_with_timeout(
            slow,
            timeout_seconds=0.1,
            default=-1
        )
        assert success is False
        assert result == -1
        assert "timed out" in error.lower()
    
    def test_exception_is_caught(self):
        """Test that exceptions are caught and returned."""
        def failing():
            raise ValueError("test error")
        
        success, result, error = run_with_timeout(
            failing,
            timeout_seconds=1.0,
            default=None
        )
        assert success is False
        assert result is None
        assert "test error" in error
    
    def test_timeout_with_args(self):
        """Test timeout with function arguments."""
        def add(a, b):
            return a + b
        
        success, result, error = run_with_timeout(
            add,
            args=(2, 3),
            timeout_seconds=1.0
        )
        assert success is True
        assert result == 5
    
    def test_timeout_with_kwargs(self):
        """Test timeout with keyword arguments."""
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"
        
        success, result, error = run_with_timeout(
            greet,
            kwargs={"name": "World", "greeting": "Hi"},
            timeout_seconds=1.0
        )
        assert success is True
        assert result == "Hi, World!"
    
    def test_decorator_fast_function(self):
        """Test timeout decorator on fast function."""
        @with_timeout(1.0)
        def fast():
            return "done"
        
        result = fast()
        assert result == "done"
    
    def test_decorator_slow_function(self):
        """Test timeout decorator on slow function."""
        @with_timeout(0.1)
        def slow():
            time.sleep(5)
            return "done"
        
        with pytest.raises(TimeoutError):
            slow()


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestSecurityIntegration:
    """Integration tests combining multiple security features."""
    
    def test_sanitize_and_timeout_together(self):
        """Test using sanitization and timeout together."""
        expr = "x**2 + 2*x + 1"
        
        # First sanitize
        result = sanitize_math_expression(expr)
        assert result.safe is True
        
        # Then run with timeout
        def mock_solve(expression):
            # Simulate some computation
            return [1, -1]
        
        success, solutions, error = run_with_timeout(
            mock_solve,
            args=(result.sanitized_input,),
            timeout_seconds=1.0
        )
        assert success is True
        assert solutions == [1, -1]
    
    def test_path_validation_with_file_creation(self):
        """Test path validation before file operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            
            # Safe path
            safe_result = validate_path_within_root("output/result.txt", root)
            assert safe_result.valid is True
            
            # Unsafe path
            unsafe_result = validate_path_within_root("../secret.txt", root)
            assert unsafe_result.valid is False
    
    def test_dangerous_patterns_coverage(self):
        """Test that all dangerous patterns are defined."""
        # Ensure we have patterns for key attack vectors
        pattern_names = [desc for _, desc in DANGEROUS_PATTERNS]
        
        assert any("dunder" in p for p in pattern_names)
        assert any("eval" in p for p in pattern_names)
        assert any("exec" in p for p in pattern_names)
        assert any("import" in p.lower() for p in pattern_names)
        assert any("os" in p.lower() for p in pattern_names)
        assert any("subprocess" in p for p in pattern_names)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Edge case and boundary tests."""
    
    def test_unicode_in_expression(self):
        """Test handling unicode characters."""
        result = sanitize_math_expression("x + \u03c0")  # pi symbol
        # Should pass - unicode math symbols are fine
        assert result.safe is True
    
    def test_very_long_expression(self):
        """Test handling very long expressions."""
        expr = "x + " * 5000 + "1"  # 15001 chars
        result = sanitize_math_expression(expr)
        # Should pass but with warning
        assert result.safe is True
        assert any("long" in w.lower() for w in result.warnings)
    
    def test_case_insensitive_blocking(self):
        """Test that blocking is case-insensitive."""
        result = sanitize_math_expression("EVAL('test')")
        assert result.safe is False
        
        result = sanitize_math_expression("__IMPORT__('os')")
        assert result.safe is False
    
    def test_path_with_spaces(self):
        """Test paths with spaces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = validate_path_within_root("my dir/my file.txt", root)
            assert result.valid is True
    
    def test_path_with_dots_in_filename(self):
        """Test paths with dots in filename (not traversal)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = validate_path_within_root("file.test.txt", root)
            assert result.valid is True
    
    def test_current_directory_path(self):
        """Test ./ paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = validate_path_within_root("./file.txt", root)
            assert result.valid is True
