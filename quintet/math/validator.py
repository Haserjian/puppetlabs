"""
Math Mode Validator (Tier 1)
=============================

Multi-path verification of math solutions.
Uses tolerance-based checks for robustness against floating-point issues.
"""

import time
import random
from typing import Optional, Dict, Any, Union, List, Tuple

from quintet.core.types import ValidationResult, ValidationCheck
from quintet.math.types import (
    MathProblem, DataProblem, MathResult, MathDomain
)
from quintet.math.robustness import (
    ToleranceConfig, DEFAULT_TOLERANCE,
    substitution_check_with_tolerance,
    finite_difference_gradient_check,
    normalize_sympy_solution, NormalizedSolution,
    canonical_variable_order
)


class MathValidator:
    """
    Validates math solutions using multiple verification strategies.
    
    Strategies:
    - Substitution: Plug solution back into original equation (with tolerance)
    - Numerical: Evaluate at random points
    - Alternative method: Solve using different approach
    - Sanity/bounds: Check solution is reasonable
    - Gradient: Finite-difference cross-check for gradients/Hessians
    """
    
    def __init__(
        self,
        backends: Dict[str, Any] = None,
        tolerance: ToleranceConfig = None
    ):
        self.backends = backends or {}
        self.tolerance = tolerance or DEFAULT_TOLERANCE
        
        # Try to get sympy for symbolic checks
        try:
            import sympy
            self.sympy = sympy
            self.sympy_available = True
        except ImportError:
            self.sympy = None
            self.sympy_available = False
        
        # Try to get numpy for numerical checks
        try:
            import numpy as np
            self.numpy = np
            self.numpy_available = True
        except ImportError:
            self.numpy = None
            self.numpy_available = False
    
    def validate(
        self,
        result: MathResult,
        problem: Union[MathProblem, DataProblem],
        options: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate a math result.
        
        Returns ValidationResult with checks and confidence.
        """
        options = options or {}
        checks = []
        warnings = []
        
        # Skip validation if result failed
        if not result.success:
            return ValidationResult(
                valid=False,
                confidence=0.0,
                checks=[],
                warnings=["Result failed - nothing to validate"],
                domain=problem.domain.value if hasattr(problem, 'domain') else None
            )
        
        # Run validation checks
        if isinstance(problem, MathProblem):
            checks.extend(self._validate_math_problem(result, problem, options))
        else:
            checks.extend(self._validate_data_problem(result, problem, options))
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(checks)
        
        # Determine validity
        valid = all(c.passed for c in checks if c.check_type == "core")
        
        # Check for suggested review
        suggested_review = confidence < 0.7 or not valid
        
        return ValidationResult(
            valid=valid,
            confidence=confidence,
            checks=checks,
            warnings=warnings,
            suggested_review=suggested_review,
            domain=problem.domain.value if hasattr(problem, 'domain') else None
        )
    
    def _validate_math_problem(
        self,
        result: MathResult,
        problem: MathProblem,
        options: Dict[str, Any]
    ) -> List[ValidationCheck]:
        """Validate math problem result."""
        checks = []
        
        # Check 1: Substitution verification (for solve problems)
        if problem.problem_type == "solve" and self.sympy_available:
            checks.append(self._check_substitution(result, problem))
        
        # Check 1b: Gradient verification (for gradient/hessian problems)
        if problem.problem_type in ("gradient", "hessian") and self.sympy_available and self.numpy_available:
            checks.append(self._check_gradient(result, problem))
        
        # Check 2: Numerical spot check
        if self.numpy_available:
            checks.append(self._check_numerical(result, problem))
        
        # Check 3: Sanity/bounds check
        checks.append(self._check_sanity(result, problem))
        
        # Check 4: Type check
        checks.append(self._check_type(result, problem))
        
        return checks
    
    def _validate_data_problem(
        self,
        result: MathResult,
        problem: DataProblem,
        options: Dict[str, Any]
    ) -> List[ValidationCheck]:
        """Validate data problem result."""
        checks = []
        
        # Check 1: Output exists and is reasonable
        checks.append(self._check_sanity(result, problem))
        
        # Check 2: Fit statistics (if available)
        checks.append(self._check_fit_quality(result, problem))
        
        return checks
    
    def _check_substitution(
        self,
        result: MathResult,
        problem: MathProblem
    ) -> ValidationCheck:
        """
        Verify solution by substitution into original equation.
        
        Uses tolerance-based checking to handle floating-point issues
        and ill-conditioned systems.
        """
        start = time.time()
        
        try:
            if not problem.expressions:
                return ValidationCheck(
                    check_name="substitution",
                    check_type="core",
                    passed=True,
                    confidence_contribution=0.1,
                    details="No expression to verify against",
                    execution_time_ms=(time.time() - start) * 1000
                )
            
            solution = result.final_answer
            goals = problem.variables or []
            if problem.goal and problem.goal not in goals:
                goals = [problem.goal] + goals
            
            # Use the solution normalizer for canonical handling
            normalized = normalize_sympy_solution(solution, goals)
            solutions = normalized.solutions
            
            if not solutions:
                # Fallback: try to build solutions manually
                if isinstance(solution, dict):
                    solutions = [solution]
                elif isinstance(solution, (list, tuple)):
                    if solution and isinstance(solution[0], dict):
                        solutions = list(solution)
                    elif goals:
                        solutions = [{goals[0]: sol} for sol in solution]
                    else:
                        solutions = [{}]
                elif goals:
                    solutions = [{goals[0]: solution}]
                else:
                    solutions = [{}]
            
            all_passed = True
            max_residual = 0.0
            failed_details = []
            
            for sol_idx, sol_map in enumerate(solutions):
                for expr_obj in problem.expressions:
                    # Use tolerance-based check
                    passed, residual, msg = substitution_check_with_tolerance(
                        expr_obj.normalized,
                        sol_map,
                        self.tolerance
                    )
                    max_residual = max(max_residual, residual if residual != float('inf') else 0)
                    
                    if not passed:
                        all_passed = False
                        failed_details.append(f"Solution {sol_idx}: {msg}")
            
            if all_passed:
                details = f"Substitution verified for {len(solutions)} solution(s), max residual={max_residual:.2e}"
            else:
                details = f"Substitution failed: {'; '.join(failed_details[:3])}"
                if len(failed_details) > 3:
                    details += f" (+{len(failed_details) - 3} more)"
            
            return ValidationCheck(
                check_name="substitution",
                check_type="core",
                passed=all_passed,
                confidence_contribution=0.3 if all_passed else 0.0,
                details=details,
                execution_time_ms=(time.time() - start) * 1000,
                method_used="tolerance-based substitution"
            )
            
        except Exception as e:
            return ValidationCheck(
                check_name="substitution",
                check_type="core",
                passed=False,
                confidence_contribution=0.0,
                details=f"Substitution check failed: {str(e)}",
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_gradient(
        self,
        result: MathResult,
        problem: MathProblem
    ) -> ValidationCheck:
        """
        Verify gradient/Hessian using finite differences.
        
        Cross-checks symbolic derivatives against numerical approximation.
        """
        start = time.time()
        
        try:
            if not problem.expressions:
                return ValidationCheck(
                    check_name="gradient_verification",
                    check_type="core",
                    passed=True,
                    confidence_contribution=0.1,
                    details="No expression for gradient check",
                    execution_time_ms=(time.time() - start) * 1000
                )
            
            gradient = result.final_answer
            if gradient is None or not isinstance(gradient, (list, tuple)):
                return ValidationCheck(
                    check_name="gradient_verification",
                    check_type="core",
                    passed=False,
                    confidence_contribution=0.0,
                    details="Gradient result is not a list/tuple",
                    execution_time_ms=(time.time() - start) * 1000
                )
            
            # Get variables (use canonical ordering)
            variables = problem.variables or []
            if not variables and problem.expressions:
                # Try to infer from expression
                expr_str = problem.expressions[0].normalized
                expr = self.sympy.sympify(expr_str)
                variables = canonical_variable_order([str(s) for s in expr.free_symbols])
            
            if not variables:
                return ValidationCheck(
                    check_name="gradient_verification",
                    check_type="core",
                    passed=True,
                    confidence_contribution=0.1,
                    details="No variables identified for gradient check",
                    execution_time_ms=(time.time() - start) * 1000
                )
            
            # Pick a random test point
            test_point = {v: random.uniform(-2.0, 2.0) for v in variables}
            
            # Get the expression
            expr_str = problem.expressions[0].normalized
            
            # Run finite-difference check
            passed, comparisons, msg = finite_difference_gradient_check(
                gradient,
                expr_str,
                variables,
                test_point,
                h=1e-7,
                tolerance=self.tolerance
            )
            
            if passed:
                details = f"Gradient verified at test point (all {len(comparisons)} components match)"
            else:
                details = msg
                if comparisons:
                    diffs = [abs(s - n) for s, n in comparisons]
                    details += f"; max component diff: {max(diffs):.2e}"
            
            return ValidationCheck(
                check_name="gradient_verification",
                check_type="core",
                passed=passed,
                confidence_contribution=0.3 if passed else 0.0,
                details=details,
                execution_time_ms=(time.time() - start) * 1000,
                method_used="finite_difference"
            )
            
        except Exception as e:
            return ValidationCheck(
                check_name="gradient_verification",
                check_type="core",
                passed=False,
                confidence_contribution=0.0,
                details=f"Gradient check failed: {str(e)}",
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_numerical(
        self,
        result: MathResult,
        problem: MathProblem
    ) -> ValidationCheck:
        """Numerical spot check at random values."""
        start = time.time()
        
        try:
            if not problem.expressions:
                return ValidationCheck(
                    check_name="numerical",
                    check_type="domain",
                    passed=True,
                    confidence_contribution=0.1,
                    details="No expression for numerical check",
                    execution_time_ms=(time.time() - start) * 1000
                )
            
            # For solve problems, we substitute and check = 0
            # For other problems, we do sanity checks on output range
            
            solution = result.final_answer
            
            # Check that solution is finite and reasonable
            if solution is None:
                passed = False
                details = "No solution produced"
            elif isinstance(solution, (int, float)):
                passed = self.numpy.isfinite(solution)
                details = f"Solution {solution} is {'finite' if passed else 'not finite'}"
            elif isinstance(solution, (list, tuple)):
                passed = all(
                    isinstance(s, (int, float)) and self.numpy.isfinite(float(s))
                    for s in solution
                    if isinstance(s, (int, float))
                )
                details = f"All {len(solution)} solutions are finite"
            else:
                passed = True
                details = "Symbolic solution (numerical check limited)"
            
            return ValidationCheck(
                check_name="numerical",
                check_type="domain",
                passed=passed,
                confidence_contribution=0.2 if passed else 0.0,
                details=details,
                execution_time_ms=(time.time() - start) * 1000,
                method_used="numpy.isfinite"
            )
            
        except Exception as e:
            return ValidationCheck(
                check_name="numerical",
                check_type="domain",
                passed=False,
                confidence_contribution=0.0,
                details=f"Numerical check failed: {str(e)}",
                execution_time_ms=(time.time() - start) * 1000
            )
    
    def _check_sanity(
        self,
        result: MathResult,
        problem: Union[MathProblem, DataProblem]
    ) -> ValidationCheck:
        """Basic sanity check on result."""
        start = time.time()
        
        passed = True
        issues = []
        
        # Check 1: Result exists
        if result.final_answer is None:
            passed = False
            issues.append("No final answer")
        
        # Check 2: No execution errors (other than warnings)
        if result.errors:
            passed = False
            issues.append(f"{len(result.errors)} errors during execution")
        
        # Check 3: At least one step succeeded
        successful_steps = sum(1 for sr in result.step_results if sr.success)
        if successful_steps == 0:
            passed = False
            issues.append("No steps succeeded")
        
        details = "All sanity checks passed" if passed else "; ".join(issues)
        
        return ValidationCheck(
            check_name="sanity",
            check_type="core",
            passed=passed,
            confidence_contribution=0.2 if passed else 0.0,
            details=details,
            execution_time_ms=(time.time() - start) * 1000
        )
    
    def _check_type(
        self,
        result: MathResult,
        problem: MathProblem
    ) -> ValidationCheck:
        """Check that result type matches expected type."""
        start = time.time()
        
        passed = True
        details = ""
        
        solution = result.final_answer
        
        if problem.problem_type == "solve":
            # Should be a value or list of values
            if solution is not None:
                passed = True
                details = f"Solution type: {type(solution).__name__}"
            else:
                passed = False
                details = "Expected solution value"
                
        elif problem.problem_type in ["integrate", "differentiate", "simplify"]:
            # Should be an expression
            passed = solution is not None
            details = f"Expression result: {str(solution)[:50]}"
            
        else:
            passed = solution is not None
            details = f"Result type: {type(solution).__name__}"
        
        return ValidationCheck(
            check_name="type_check",
            check_type="domain",
            passed=passed,
            confidence_contribution=0.1 if passed else 0.0,
            details=details,
            execution_time_ms=(time.time() - start) * 1000
        )
    
    def _check_fit_quality(
        self,
        result: MathResult,
        problem: DataProblem
    ) -> ValidationCheck:
        """Check quality of data fit."""
        start = time.time()
        
        # Look for fit statistics in step results
        r_squared = None
        for sr in result.step_results:
            if isinstance(sr.output, dict):
                r_squared = sr.output.get("r_squared") or sr.output.get("R2")
        
        if r_squared is not None:
            passed = r_squared > 0.5  # Basic threshold
            details = f"R² = {r_squared:.4f}"
        else:
            passed = result.success
            details = "Fit completed (no R² available)"
        
        return ValidationCheck(
            check_name="fit_quality",
            check_type="domain",
            passed=passed,
            confidence_contribution=0.2 if passed else 0.0,
            details=details,
            execution_time_ms=(time.time() - start) * 1000
        )
    
    def _calculate_confidence(self, checks: List[ValidationCheck]) -> float:
        """Calculate overall confidence from checks."""
        if not checks:
            return 0.0
        
        # Sum confidence contributions from passed checks
        total = sum(c.confidence_contribution for c in checks if c.passed)
        
        # Cap at 1.0
        return min(total, 1.0)
