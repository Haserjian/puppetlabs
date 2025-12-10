"""
Math Mode Executor (Tier 1)
============================

Executes solution plans by dispatching subgoals to backends.
"""

import time
import uuid
from typing import Dict, Any, Optional, List, Union

from quintet.math.types import (
    MathProblem, DataProblem, MathExpression,
    SolutionPlan, Subgoal, StepResult, MathResult
)
from quintet.math.backends.base import MathBackend
from quintet.math.robustness import normalize_sympy_solution


class MathExecutor:
    """
    Executes solution plans by running subgoals against backends.
    
    Walks the DAG in topological order, passing outputs between steps.
    """
    
    def __init__(self, backends: Dict[str, MathBackend] = None):
        self.backends = backends or {}
        self._step_outputs: Dict[str, Any] = {}
    
    def execute(
        self,
        plan: SolutionPlan,
        problem: Union[MathProblem, DataProblem],
        options: Optional[Dict[str, Any]] = None
    ) -> MathResult:
        """
        Execute a solution plan.
        
        Returns MathResult with step results and final answer.
        """
        options = options or {}
        start_time = time.time()
        
        self._step_outputs = {}
        step_results = []
        errors = []
        warnings = []
        final_answer = None
        final_latex = None
        
        # Execute subgoals in order
        for subgoal_id in plan.execution_order:
            subgoal = self._get_subgoal(plan, subgoal_id)
            if not subgoal:
                errors.append(f"Subgoal not found: {subgoal_id}")
                continue
            
            # Skip verification subgoals during execution (handled by validator)
            if subgoal.is_verification:
                continue
            
            # Execute the subgoal
            step_result = self._execute_subgoal(subgoal, problem, options)
            step_results.append(step_result)
            
            if step_result.success:
                # Store output for dependent steps
                self._step_outputs[subgoal_id] = step_result.output
                
                # Track final answer (last successful non-verification step)
                final_answer = step_result.output
                final_latex = step_result.output_latex
            else:
                errors.extend(step_result.errors)
                # Don't break - try to continue if possible
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Determine overall success
        success = len(errors) == 0 and final_answer is not None
        
        return MathResult(
            success=success,
            final_answer=final_answer,
            final_answer_latex=final_latex,
            step_results=step_results,
            execution_time_ms=elapsed_ms,
            errors=errors,
            warnings=warnings
        )
    
    def _get_subgoal(self, plan: SolutionPlan, subgoal_id: str) -> Optional[Subgoal]:
        """Get a subgoal by ID."""
        for sg in plan.subgoals:
            if sg.subgoal_id == subgoal_id:
                return sg
        return None
    
    def _execute_subgoal(
        self,
        subgoal: Subgoal,
        problem: Union[MathProblem, DataProblem],
        options: Dict[str, Any]
    ) -> StepResult:
        """Execute a single subgoal."""
        start_time = time.time()
        step_id = f"step-{uuid.uuid4().hex[:8]}"
        
        # Get backend
        backend = self.backends.get(subgoal.backend)
        if not backend:
            return StepResult(
                step_id=step_id,
                subgoal_id=subgoal.subgoal_id,
                success=False,
                output=None,
                errors=[f"Backend not available: {subgoal.backend}"]
            )
        
        # Check if backend supports the operation
        if hasattr(backend, 'supports') and not backend.supports(subgoal.method):
            return StepResult(
                step_id=step_id,
                subgoal_id=subgoal.subgoal_id,
                success=False,
                output=None,
                errors=[f"Backend {subgoal.backend} does not support operation: {subgoal.method}"]
            )
        
        # Prepare inputs
        inputs = self._prepare_inputs(subgoal, problem)
        
        # Execute
        try:
            result = backend.execute(
                operation=subgoal.method,
                inputs=inputs,
                options=options
            )
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Post-process certain operations for friendlier shapes
            output = result.output
            output_latex = None

            # For SymPy solve(), normalize solutions so that:
            # - single-variable problems return a flat list of values
            # - systems return a dict (or list of dicts) with string keys
            if subgoal.method == "solve" and backend.name == "sympy" and output is not None:
                # Expected variables, if the parser found any
                expected_vars: List[str] = []
                if isinstance(problem, MathProblem) and problem.variables:
                    expected_vars = problem.variables
                norm = normalize_sympy_solution(output, expected_vars)

                if norm.variable_order and len(norm.variable_order) > 1:
                    # System: prefer the primary solution dict
                    output = norm.primary_solution or {}
                else:
                    # Single variable: flatten into list of values
                    vals: List[Any] = []
                    for sol in norm.solutions:
                        vals.extend(sol.values())
                    output = vals

                result.output = output

            # Convert output to LaTeX if possible
            output_latex = None
            if result.success and output is not None:
                output_latex = self._to_latex(output, backend)
            
            return StepResult(
                step_id=step_id,
                subgoal_id=subgoal.subgoal_id,
                success=result.success,
                output=output,
                output_latex=output_latex,
                backend_used=subgoal.backend,
                code_executed=None,  # BackendResult doesn't have code tracking
                execution_time_ms=elapsed_ms,
                logs=result.logs or [],
                errors=result.errors or []
            )
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return StepResult(
                step_id=step_id,
                subgoal_id=subgoal.subgoal_id,
                success=False,
                output=None,
                execution_time_ms=elapsed_ms,
                errors=[f"Execution error: {str(e)}"]
            )
    
    def _prepare_inputs(
        self,
        subgoal: Subgoal,
        problem: Union[MathProblem, DataProblem]
    ) -> Dict[str, Any]:
        """Prepare inputs for a subgoal execution."""
        inputs = {}
        
        # Add expression(s) from problem if available
        if isinstance(problem, MathProblem) and problem.expressions:
            if len(problem.expressions) > 1:
                inputs["expressions"] = [e.normalized or e.raw for e in problem.expressions]
            else:
                expr = problem.expressions[0]
                inputs["expression"] = expr.normalized or expr.raw
                inputs["raw_expression"] = expr.raw
        
        # Add variables
        if isinstance(problem, MathProblem) and problem.variables:
            if len(problem.variables) > 1:
                inputs["variables"] = problem.variables
            else:
                inputs["variable"] = problem.variables[0]
        
        # Add goal if it looks like a variable (single letter)
        if isinstance(problem, MathProblem) and problem.goal:
            if len(problem.goal) == 1 and problem.goal.isalpha():
                inputs["variable"] = problem.goal
        
        # Add outputs from previous steps
        for input_ref in subgoal.inputs:
            if input_ref in self._step_outputs:
                previous_output = self._step_outputs[input_ref]
                inputs["previous_output"] = previous_output
                # Also map to common input names backends expect
                if "expression" not in inputs and previous_output is not None:
                    inputs["expression"] = str(previous_output)
        
        return inputs
    
    def _to_latex(self, output: Any, backend: MathBackend) -> Optional[str]:
        """Convert output to LaTeX if possible."""
        if output is None:
            return None
        
        # Try SymPy's latex conversion
        if backend.name == "sympy":
            try:
                import sympy
                if hasattr(sympy, 'latex'):
                    return sympy.latex(output)
            except:
                pass
        
        # Fallback to string
        return str(output)
    
    def get_step_output(self, subgoal_id: str) -> Optional[Any]:
        """Get the output of a previously executed subgoal."""
        return self._step_outputs.get(subgoal_id)
    
    def clear_outputs(self):
        """Clear cached step outputs."""
        self._step_outputs = {}
