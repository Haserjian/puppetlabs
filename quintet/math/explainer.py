"""
Math Mode Explainer (Tier 1)
=============================

Generates step-by-step explanations of solutions.
"""

from typing import Optional, Dict, Any, Union, List

from quintet.math.types import (
    MathProblem, DataProblem, MathResult, SolutionPlan,
    Explanation, ExplanationStep, ExplainerMode
)


class MathExplainer:
    """
    Generates human-readable explanations of math solutions.
    
    Supports two modes:
    - PEDAGOGICAL: Educational, detailed, assumes limited background
    - EXPERT: Concise, assumes mathematical maturity
    """
    
    def __init__(self, mode: ExplainerMode = ExplainerMode.PEDAGOGICAL):
        self.mode = mode
    
    def explain(
        self,
        result: MathResult,
        problem: Union[MathProblem, DataProblem],
        plan: SolutionPlan,
        options: Optional[Dict[str, Any]] = None
    ) -> Explanation:
        """
        Generate explanation for a solution.
        """
        options = options or {}
        mode = options.get("mode", self.mode)
        
        if isinstance(problem, DataProblem):
            return self._explain_data(result, problem, plan, mode)
        else:
            return self._explain_math(result, problem, plan, mode)
    
    def _explain_math(
        self,
        result: MathResult,
        problem: MathProblem,
        plan: SolutionPlan,
        mode: ExplainerMode
    ) -> Explanation:
        """Generate explanation for math problem."""
        steps = []
        
        # Step 0: Problem understanding
        steps.append(ExplanationStep(
            step_number=0,
            title="Understanding the Problem",
            description=self._describe_problem(problem, mode),
            math_latex=self._problem_latex(problem)
        ))
        
        # Steps from execution
        for i, sr in enumerate(result.step_results):
            if sr.is_verification if hasattr(sr, 'is_verification') else False:
                continue  # Skip verification in main explanation
            
            step = ExplanationStep(
                step_number=i + 1,
                title=self._step_title(sr.subgoal_id, plan),
                description=self._step_description(sr, problem, mode),
                math_latex=sr.output_latex,
                justification=self._step_justification(sr, mode)
            )
            steps.append(step)
        
        # Final step: conclusion
        steps.append(ExplanationStep(
            step_number=len(steps),
            title="Conclusion",
            description=self._conclusion(result, problem, mode),
            math_latex=result.final_answer_latex
        ))
        
        # Build summary
        summary = self._build_summary(result, problem, mode)
        
        # Build final statement
        final_statement = self._build_final_statement(result, problem)
        
        # Build full LaTeX
        latex_full = self._build_full_latex(steps)
        
        return Explanation(
            mode=mode,
            summary=summary,
            steps=steps,
            final_statement=final_statement,
            latex_full=latex_full
        )
    
    def _explain_data(
        self,
        result: MathResult,
        problem: DataProblem,
        plan: SolutionPlan,
        mode: ExplainerMode
    ) -> Explanation:
        """Generate explanation for data problem."""
        steps = []
        
        # Step 0: Problem setup
        steps.append(ExplanationStep(
            step_number=0,
            title="Problem Setup",
            description=f"We are asked to {problem.problem_type} using the given data.",
            justification="Data analysis starts with understanding what we're trying to find."
        ))
        
        # Step 1: Data preparation
        steps.append(ExplanationStep(
            step_number=1,
            title="Data Preparation",
            description=self._describe_data_prep(problem, mode)
        ))
        
        # Step 2: Model fitting
        steps.append(ExplanationStep(
            step_number=2,
            title="Model Fitting",
            description=self._describe_fitting(result, problem, mode),
            math_latex=result.final_answer_latex
        ))
        
        # Step 3: Interpretation
        steps.append(ExplanationStep(
            step_number=3,
            title="Interpretation",
            description=self._interpret_data_result(result, problem, mode)
        ))
        
        return Explanation(
            mode=mode,
            summary=f"Performed {problem.problem_type} analysis on the provided data.",
            steps=steps,
            final_statement=str(result.final_answer)
        )
    
    def _describe_problem(self, problem: MathProblem, mode: ExplainerMode) -> str:
        """Describe the problem in words."""
        if mode == ExplainerMode.EXPERT:
            return f"Given: {problem.description[:100]}"
        
        problem_types = {
            "solve": "find the value(s) that satisfy",
            "integrate": "find the antiderivative of",
            "differentiate": "find the derivative of",
            "simplify": "simplify",
            "factor": "factor",
            "expand": "expand",
            "prove": "prove",
            "optimize": "find the optimal value of"
        }
        
        verb = problem_types.get(problem.problem_type, "evaluate")
        
        if problem.expressions:
            expr = problem.expressions[0].raw
            return f"We need to {verb} the expression: {expr}"
        else:
            return f"We need to {verb}: {problem.description}"
    
    def _problem_latex(self, problem: MathProblem) -> Optional[str]:
        """Get LaTeX representation of problem."""
        if problem.expressions and problem.expressions[0].latex:
            return problem.expressions[0].latex
        return None
    
    def _step_title(self, subgoal_id: str, plan: SolutionPlan) -> str:
        """Get title for a step."""
        for sg in plan.subgoals:
            if sg.subgoal_id == subgoal_id:
                return sg.description
        return subgoal_id.replace("sg_", "").replace("_", " ").title()
    
    def _step_description(
        self,
        step_result,
        problem: MathProblem,
        mode: ExplainerMode
    ) -> str:
        """Describe what happened in a step."""
        if not step_result.success:
            return f"This step encountered an error: {'; '.join(step_result.errors)}"
        
        if mode == ExplainerMode.EXPERT:
            return f"Result: {step_result.output}"
        
        # Pedagogical mode
        method = step_result.code_executed or step_result.backend_used
        output = step_result.output
        
        return f"Using {method}, we compute: {output}"
    
    def _step_justification(self, step_result, mode: ExplainerMode) -> Optional[str]:
        """Provide justification for a step."""
        if mode == ExplainerMode.EXPERT:
            return None
        
        method = step_result.backend_used
        
        justifications = {
            "sympy": "We use symbolic computation to get an exact result.",
            "numeric": "We use numerical methods for efficient computation."
        }
        
        return justifications.get(method, f"Computed using {method}")
    
    def _conclusion(
        self,
        result: MathResult,
        problem: MathProblem,
        mode: ExplainerMode
    ) -> str:
        """Build conclusion text."""
        if not result.success:
            return "The problem could not be solved. Please check the input and try again."
        
        answer = result.final_answer
        
        if mode == ExplainerMode.EXPERT:
            return f"∴ {answer}"
        
        # Pedagogical
        if problem.problem_type == "solve":
            if problem.goal:
                return f"Therefore, {problem.goal} = {answer}"
            return f"The solution is: {answer}"
        elif problem.problem_type == "integrate":
            return f"The integral evaluates to: {answer} + C (constant of integration)"
        elif problem.problem_type == "differentiate":
            return f"The derivative is: {answer}"
        else:
            return f"The result is: {answer}"
    
    def _build_summary(
        self,
        result: MathResult,
        problem: MathProblem,
        mode: ExplainerMode
    ) -> str:
        """Build one-paragraph summary."""
        if mode == ExplainerMode.EXPERT:
            return f"{problem.problem_type.title()}: {result.final_answer}"
        
        steps_count = len([sr for sr in result.step_results if sr.success])
        time_ms = result.execution_time_ms
        
        return (
            f"This {problem.domain.value} problem required {steps_count} computation steps "
            f"and was solved in {time_ms:.1f}ms. "
            f"The final answer is: {result.final_answer}"
        )
    
    def _build_final_statement(
        self,
        result: MathResult,
        problem: MathProblem
    ) -> str:
        """Build final answer statement."""
        if problem.goal:
            return f"{problem.goal} = {result.final_answer}"
        return str(result.final_answer)
    
    def _build_full_latex(self, steps: List[ExplanationStep]) -> Optional[str]:
        """Build full LaTeX document."""
        latex_parts = []
        
        for step in steps:
            if step.math_latex:
                latex_parts.append(f"% Step {step.step_number}: {step.title}")
                latex_parts.append(step.math_latex)
        
        if latex_parts:
            return "\n".join(latex_parts)
        return None
    
    def _describe_data_prep(self, problem: DataProblem, mode: ExplainerMode) -> str:
        """Describe data preparation."""
        if problem.data_inline:
            n = len(list(problem.data_inline.values())[0]) if problem.data_inline else 0
            return f"Loaded inline data with {n} observations."
        elif problem.data_source:
            return f"Loaded data from: {problem.data_source}"
        return "Prepared the data for analysis."
    
    def _describe_fitting(
        self,
        result: MathResult,
        problem: DataProblem,
        mode: ExplainerMode
    ) -> str:
        """Describe model fitting."""
        model = problem.model_hint or "the appropriate model"
        return f"Fitted {model} to the data to predict {problem.target_variable}."
    
    def _interpret_data_result(
        self,
        result: MathResult,
        problem: DataProblem,
        mode: ExplainerMode
    ) -> str:
        """Interpret data analysis result."""
        return f"The model parameters are: {result.final_answer}"


