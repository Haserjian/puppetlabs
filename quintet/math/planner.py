"""
Math Mode Planner (Tier 1)
===========================

Creates solution plans (DAGs of subgoals) for math problems.

Capability-aware: Checks backend capabilities before emitting subgoals.
"""

import uuid
from typing import List, Optional, Dict, Any, Union, Tuple

from quintet.math.types import (
    MathProblem, DataProblem, MathDomain,
    Subgoal, SolutionPlan
)
from quintet.math.robustness import (
    MathCapability, check_capability, get_capable_backends,
    estimate_complexity, ProblemComplexity,
    canonical_variable_order
)


class SolutionPlanner:
    """
    Plans solution strategies for math problems.
    
    Creates a DAG of subgoals that the executor will traverse.
    
    Capability-aware: Checks backend capabilities before emitting subgoals.
    Complexity-aware: Estimates problem complexity and may recommend
    numeric-first approaches for large systems.
    """
    
    def __init__(self, available_backends: List[str] = None):
        self.available_backends = available_backends or ["sympy", "numeric"]
    
    def _check_capability(self, capability: MathCapability) -> Tuple[bool, str, List[str]]:
        """
        Check if any available backend supports a capability.
        
        Returns: (available, reason, capable_backends)
        """
        capable = get_capable_backends(capability)
        available_capable = [b for b in capable if b in self.available_backends]
        
        if available_capable:
            return True, "OK", available_capable
        else:
            return False, f"No backend supports {capability.value}", []
    
    def plan(
        self,
        problem: Union[MathProblem, DataProblem],
        options: Optional[Dict[str, Any]] = None
    ) -> SolutionPlan:
        """
        Create a solution plan for the problem.
        """
        options = options or {}
        
        if isinstance(problem, DataProblem):
            return self._plan_data_problem(problem, options)
        else:
            return self._plan_math_problem(problem, options)
    
    def _plan_math_problem(
        self, 
        problem: MathProblem, 
        options: Dict[str, Any]
    ) -> SolutionPlan:
        """
        Plan for standard math problem.
        
        Checks capabilities and estimates complexity before planning.
        """
        subgoals = []
        
        # Estimate complexity for routing hints
        expressions = [e.normalized for e in (problem.expressions or [])]
        variables = problem.variables or []
        complexity = estimate_complexity(expressions, variables)
        
        # Store complexity in options for downstream use
        options["_complexity"] = complexity
        
        # Strategy depends on problem type and domain
        if problem.problem_type == "solve":
            subgoals = self._plan_solve(problem, complexity)
        elif problem.problem_type == "integrate":
            subgoals = self._plan_integrate(problem)
        elif problem.problem_type == "differentiate":
            subgoals = self._plan_differentiate(problem)
        elif problem.problem_type == "simplify":
            subgoals = self._plan_simplify(problem)
        elif problem.problem_type == "factor":
            subgoals = self._plan_factor(problem)
        elif problem.problem_type == "expand":
            subgoals = self._plan_expand(problem)
        elif problem.problem_type == "prove":
            subgoals = self._plan_prove(problem)
        elif problem.problem_type == "optimize":
            subgoals = self._plan_optimize(problem, complexity)
        elif problem.problem_type == "gradient":
            subgoals = self._plan_gradient(problem)
        elif problem.problem_type == "hessian":
            subgoals = self._plan_hessian(problem)
        else:
            # Default: compute/evaluate
            subgoals = self._plan_compute(problem)
        
        # Add verification subgoals
        verification_subgoals = self._add_verification(problem, subgoals)
        all_subgoals = subgoals + verification_subgoals
        
        # Determine execution order (topological sort)
        execution_order = [sg.subgoal_id for sg in all_subgoals]
        
        # Determine complexity
        complexity = "simple"
        if len(all_subgoals) > 3:
            complexity = "moderate"
        if len(all_subgoals) > 6:
            complexity = "complex"
        
        # Determine required backends
        backends_required = list(set(sg.backend for sg in all_subgoals))
        
        return SolutionPlan(
            plan_id=str(uuid.uuid4()),
            problem_id=problem.problem_id,
            subgoals=all_subgoals,
            execution_order=execution_order,
            estimated_complexity=complexity,
            backends_required=backends_required
        )
    
    def _plan_solve(
        self,
        problem: MathProblem,
        complexity: ProblemComplexity = None
    ) -> List[Subgoal]:
        """
        Plan for solving equations.
        
        Uses complexity info to choose between symbolic and numeric paths.
        """
        subgoals = []
        
        # Determine if this is a system (multiple equations/variables)
        is_system = (
            (complexity and complexity.num_equations > 1) or
            (problem.expressions and len(problem.expressions) > 1) or
            (problem.variables and len(problem.variables) > 1)
        )
        
        # Check capability
        cap = MathCapability.SOLVE_SYSTEM if is_system else MathCapability.SOLVE_SINGLE
        available, reason, backends = self._check_capability(cap)
        
        if not available:
            # Return a failed subgoal that will report the capability error
            return [Subgoal(
                subgoal_id="sg_solve_unavailable",
                description=f"Capability not available: {reason}",
                method="error",
                backend="none",
                inputs=[],
                expected_output=f"Error: {reason}"
            )]
        
        # Choose backend and approach based on complexity
        if complexity and complexity.should_prefer_numeric() and complexity.is_linear:
            # For large linear systems, prefer numeric
            if self._check_capability(MathCapability.LINEAR_SOLVE)[0]:
                subgoals.append(Subgoal(
                    subgoal_id="sg_solve_numeric",
                    description="Solve linear system numerically",
                    method="linear_solve",
                    backend="numeric",
                    inputs=[expr.raw for expr in problem.expressions] if problem.expressions else [],
                    expected_output="Numerical solution vector"
                ))
                return subgoals
        
        # Default: symbolic solve with SymPy
        subgoals.append(Subgoal(
            subgoal_id="sg_solve",
            description="Solve equation/system" if is_system else "Solve equation",
            method="solve",
            backend="sympy",
            inputs=[expr.raw for expr in problem.expressions] if problem.expressions else [],
            expected_output="Solution(s) to the equation or system"
        ))
        
        return subgoals
    
    def _plan_integrate(self, problem: MathProblem) -> List[Subgoal]:
        """Plan for integration."""
        subgoals = []
        
        subgoals.append(Subgoal(
            subgoal_id="sg_integrate",
            description="Compute the integral",
            method="integrate",
            backend="sympy",
            inputs=[expr.raw for expr in problem.expressions],
            expected_output="Antiderivative or definite integral value"
        ))
        
        return subgoals

    def _plan_gradient(self, problem: MathProblem) -> List[Subgoal]:
        """Plan for gradients."""
        return [Subgoal(
            subgoal_id="sg_gradient",
            description="Compute gradient",
            method="gradient",
            backend="sympy",
            inputs=[expr.raw for expr in problem.expressions],
            expected_output="Gradient vector"
        )]

    def _plan_hessian(self, problem: MathProblem) -> List[Subgoal]:
        """Plan for Hessians."""
        return [Subgoal(
            subgoal_id="sg_hessian",
            description="Compute Hessian",
            method="hessian",
            backend="sympy",
            inputs=[expr.raw for expr in problem.expressions],
            expected_output="Hessian matrix"
        )]
    
    def _plan_differentiate(self, problem: MathProblem) -> List[Subgoal]:
        """Plan for differentiation."""
        subgoals = []
        
        subgoals.append(Subgoal(
            subgoal_id="sg_differentiate",
            description="Compute the derivative",
            method="differentiate",
            backend="sympy",
            inputs=[expr.raw for expr in problem.expressions],
            expected_output="Derivative of the expression"
        ))
        
        return subgoals
    
    def _plan_simplify(self, problem: MathProblem) -> List[Subgoal]:
        """Plan for simplification."""
        return [Subgoal(
            subgoal_id="sg_simplify",
            description="Simplify the expression",
            method="simplify",
            backend="sympy",
            inputs=[expr.raw for expr in problem.expressions],
            expected_output="Simplified expression"
        )]
    
    def _plan_factor(self, problem: MathProblem) -> List[Subgoal]:
        """Plan for factoring."""
        return [Subgoal(
            subgoal_id="sg_factor",
            description="Factor the expression",
            method="factor",
            backend="sympy",
            inputs=[expr.raw for expr in problem.expressions],
            expected_output="Factored form"
        )]
    
    def _plan_expand(self, problem: MathProblem) -> List[Subgoal]:
        """Plan for expansion."""
        return [Subgoal(
            subgoal_id="sg_expand",
            description="Expand the expression",
            method="expand",
            backend="sympy",
            inputs=[expr.raw for expr in problem.expressions],
            expected_output="Expanded form"
        )]
    
    def _plan_prove(self, problem: MathProblem) -> List[Subgoal]:
        """Plan for proofs."""
        subgoals = []
        
        # For proofs, we simplify both sides and check equality
        # SymPy's simplify() handles the parsing internally
        subgoals.append(Subgoal(
            subgoal_id="sg_simplify",
            description="Simplify expression to verify equality/identity",
            method="simplify",
            backend="sympy",
            inputs=[expr.raw for expr in problem.expressions] if problem.expressions else [],
            expected_output="Simplified form (should equal 0 or True for valid proofs)"
        ))
        
        return subgoals
    
    def _plan_optimize(
        self,
        problem: MathProblem,
        complexity: ProblemComplexity = None
    ) -> List[Subgoal]:
        """
        Plan for optimization.
        
        Checks capabilities for numeric optimization (SciPy).
        """
        subgoals = []
        
        # Step 1: Symbolic differentiation to find critical points
        subgoals.append(Subgoal(
            subgoal_id="sg_critical_points",
            description="Find critical points by setting derivative to zero",
            method="solve",
            backend="sympy",
            inputs=[expr.raw for expr in problem.expressions],
            expected_output="Critical points"
        ))
        
        # Step 2: Numerical verification if SciPy is available
        can_minimize, reason, _ = self._check_capability(MathCapability.MINIMIZE)
        if can_minimize and "numeric" in self.available_backends:
            subgoals.append(Subgoal(
                subgoal_id="sg_numeric_verify",
                description="Verify optimal value numerically",
                method="minimize",
                backend="numeric",
                inputs=["sg_critical_points"],
                expected_output="Numerical confirmation"
            ))
        
        return subgoals
    
    def _plan_compute(self, problem: MathProblem) -> List[Subgoal]:
        """Default compute plan."""
        return [Subgoal(
            subgoal_id="sg_compute",
            description="Evaluate/compute the expression",
            method="simplify",
            backend="sympy",
            inputs=[expr.raw for expr in problem.expressions],
            expected_output="Computed result"
        )]
    
    def _plan_data_problem(
        self, 
        problem: DataProblem, 
        options: Dict[str, Any]
    ) -> SolutionPlan:
        """Plan for data/stats problems."""
        subgoals = []
        
        # Step 1: Load/prepare data
        subgoals.append(Subgoal(
            subgoal_id="sg_load_data",
            description="Load and prepare data",
            method="numeric",
            backend="numeric",
            inputs=[],
            expected_output="Prepared data arrays"
        ))
        
        # Step 2: Fit model
        subgoals.append(Subgoal(
            subgoal_id="sg_fit",
            description=f"Fit {problem.model_hint or 'model'} to data",
            method=problem.problem_type,
            backend="numeric",
            inputs=["sg_load_data"],
            expected_output="Fitted model parameters"
        ))
        
        # Step 3: Evaluate fit
        subgoals.append(Subgoal(
            subgoal_id="sg_evaluate",
            description="Evaluate model fit",
            method="evaluate",
            backend="numeric",
            inputs=["sg_fit"],
            expected_output="Fit statistics (R², MSE, etc.)",
            is_verification=True
        ))
        
        return SolutionPlan(
            plan_id=str(uuid.uuid4()),
            problem_id=problem.problem_id,
            subgoals=subgoals,
            execution_order=[sg.subgoal_id for sg in subgoals],
            estimated_complexity="moderate",
            backends_required=["numeric"]
        )
    
    def _add_verification(
        self, 
        problem: MathProblem, 
        main_subgoals: List[Subgoal]
    ) -> List[Subgoal]:
        """Add verification subgoals."""
        verification = []
        
        # Always add numeric spot check if numeric backend available
        if "numeric" in self.available_backends and main_subgoals:
            last_subgoal = main_subgoals[-1].subgoal_id
            verification.append(Subgoal(
                subgoal_id="sg_verify_numeric",
                description="Numerical verification with random values",
                method="evaluate",
                backend="numeric",
                inputs=[last_subgoal],
                expected_output="Numerical confirmation",
                is_verification=True
            ))
        
        # For solve problems: substitution check
        if problem.problem_type == "solve" and main_subgoals:
            last_subgoal = main_subgoals[-1].subgoal_id
            verification.append(Subgoal(
                subgoal_id="sg_verify_substitution",
                description="Verify solution by substitution",
                method="simplify",
                backend="sympy",
                inputs=[last_subgoal],
                expected_output="0 (confirming solution)",
                is_verification=True
            ))
        
        return verification
