"""
Math Mode Types - Math-Specific Only
=====================================

This module defines ONLY math-specific types.
All shared types are imported from quintet.core.types.

DO NOT redefine: ValidationResult, ColorTileGrid, CognitionSummary, etc.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from enum import Enum
import uuid

# Import shared types from core - DO NOT REDEFINE THESE
from quintet.core.types import (
    ModeResultBase,
    ValidationResult,
    ValidationCheck,
    ContextFlowEntry,
    ColorTileGrid,
    CognitionSummary,
    IncompletenessAssessment,
    WorldImpactAssessment,
    ModeError,
    ErrorCode,
    SPEC_VERSION,
)


# =============================================================================
# MATH INTENT
# =============================================================================

class MathDomain(Enum):
    """Supported math domains."""
    # Tier 1 (Required)
    ALGEBRA = "algebra"
    CALCULUS = "calculus"
    LINEAR_ALGEBRA = "linear_algebra"
    PROBABILITY = "probability"
    NUMBER_THEORY = "number_theory"
    
    # Tier 2 (Optional packs)
    OPTIMIZATION = "optimization"
    STATISTICS = "statistics"
    DIFFERENTIAL_EQUATIONS = "differential_equations"
    MACHINE_LEARNING = "machine_learning"
    PDE = "pde"
    FORMAL = "formal"


@dataclass
class MathIntent:
    """Classification of a math problem's intent."""
    is_math: bool
    confidence: float           # 0.0-1.0
    domain: MathDomain
    problem_type: str           # "solve", "prove", "compute", "optimize", "fit", "analyze"
    requires_explanation: bool
    data_problem: bool          # Requires dataset
    compute_tier: str = "standard"  # "light" | "standard" | "deep_search"
    keywords_matched: List[str] = field(default_factory=list)
    raw_query: str = ""


# =============================================================================
# MATH EXPRESSIONS
# =============================================================================

@dataclass
class MathExpression:
    """Parsed mathematical expression."""
    raw: str                                # Original text
    normalized: str                         # Cleaned/standardized
    sympy_expr: Optional[Any] = None        # SymPy expression object
    latex: Optional[str] = None             # LaTeX representation
    variables: List[str] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw": self.raw,
            "normalized": self.normalized,
            "latex": self.latex,
            "variables": self.variables,
            "operations": self.operations
        }


# =============================================================================
# PROBLEM TYPES
# =============================================================================

@dataclass
class MathProblem:
    """Structured representation of a math problem."""
    problem_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    domain: MathDomain = MathDomain.ALGEBRA
    problem_type: str = "solve"             # "solve", "prove", "compute", "simplify", etc.
    description: str = ""
    
    expressions: List[MathExpression] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    goal: Optional[str] = None              # What we're solving for
    
    # Original input
    raw_input: str = ""
    parsed_successfully: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "domain": self.domain.value,
            "problem_type": self.problem_type,
            "description": self.description,
            "expressions": [e.to_dict() for e in self.expressions],
            "variables": self.variables,
            "constraints": self.constraints,
            "assumptions": self.assumptions,
            "goal": self.goal
        }


@dataclass
class DataProblem:
    """Problem involving data/statistics."""
    problem_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    domain: MathDomain = MathDomain.STATISTICS
    problem_type: str = "fit"               # "fit", "predict", "infer", "test"
    description: str = ""
    
    data_source: Optional[str] = None       # Path or description
    data_inline: Optional[Dict[str, List[Any]]] = None  # Inline data
    target_variable: Optional[str] = None
    feature_variables: List[str] = field(default_factory=list)
    model_hint: Optional[str] = None        # "linear", "logistic", "neural", etc.
    
    raw_input: str = ""
    parsed_successfully: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "domain": self.domain.value,
            "problem_type": self.problem_type,
            "description": self.description,
            "data_source": self.data_source,
            "target_variable": self.target_variable,
            "feature_variables": self.feature_variables,
            "model_hint": self.model_hint
        }


# =============================================================================
# SOLUTION PLANNING
# =============================================================================

@dataclass
class Subgoal:
    """Single step in a solution plan."""
    subgoal_id: str
    description: str
    method: str                 # "symbolic", "numeric", "substitution", etc.
    backend: str                # "sympy", "numpy", "scipy", etc.
    inputs: List[str]           # References to previous subgoals or expressions
    expected_output: str        # Description of what this produces
    priority: int = 0
    is_verification: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "subgoal_id": self.subgoal_id,
            "description": self.description,
            "method": self.method,
            "backend": self.backend,
            "inputs": self.inputs,
            "expected_output": self.expected_output,
            "is_verification": self.is_verification
        }


@dataclass
class SolutionPlan:
    """DAG of subgoals for solving a problem."""
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    problem_id: str = ""
    subgoals: List[Subgoal] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)  # Topological order
    estimated_complexity: str = "simple"    # "simple" | "moderate" | "complex"
    backends_required: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "problem_id": self.problem_id,
            "subgoals": [s.to_dict() for s in self.subgoals],
            "execution_order": self.execution_order,
            "estimated_complexity": self.estimated_complexity,
            "backends_required": self.backends_required
        }


# =============================================================================
# EXECUTION RESULTS
# =============================================================================

@dataclass
class StepResult:
    """Result of executing a single subgoal."""
    step_id: str
    subgoal_id: str
    success: bool
    
    output: Any                             # Raw output
    output_expr: Optional[MathExpression] = None  # Parsed output
    output_latex: Optional[str] = None
    
    backend_used: str = ""
    code_executed: Optional[str] = None     # For audit
    execution_time_ms: float = 0.0
    
    logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "subgoal_id": self.subgoal_id,
            "success": self.success,
            "output": str(self.output),
            "output_latex": self.output_latex,
            "backend_used": self.backend_used,
            "execution_time_ms": self.execution_time_ms,
            "errors": self.errors
        }


@dataclass
class MathResult:
    """Result of solving a math problem (before validation/explanation)."""
    success: bool
    final_answer: Any
    final_answer_latex: Optional[str] = None
    final_answer_expr: Optional[MathExpression] = None
    
    step_results: List[StepResult] = field(default_factory=list)
    execution_time_ms: float = 0.0
    
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "final_answer": str(self.final_answer),
            "final_answer_latex": self.final_answer_latex,
            "step_results": [s.to_dict() for s in self.step_results],
            "execution_time_ms": self.execution_time_ms,
            "errors": self.errors,
            "warnings": self.warnings
        }


# =============================================================================
# EXPLANATION
# =============================================================================

class ExplainerMode(Enum):
    """Mode of explanation."""
    PEDAGOGICAL = "pedagogical"     # Educational, step-by-step
    EXPERT = "expert"               # Concise, assumes background


@dataclass
class ExplanationStep:
    """Single step in an explanation."""
    step_number: int
    title: str
    description: str
    math_latex: Optional[str] = None
    justification: Optional[str] = None  # Why this step
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "title": self.title,
            "description": self.description,
            "math_latex": self.math_latex,
            "justification": self.justification
        }


@dataclass
class Explanation:
    """Complete explanation of a solution."""
    mode: ExplainerMode = ExplainerMode.PEDAGOGICAL
    summary: str = ""
    steps: List[ExplanationStep] = field(default_factory=list)
    final_statement: str = ""
    latex_full: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "summary": self.summary,
            "steps": [s.to_dict() for s in self.steps],
            "final_statement": self.final_statement,
            "latex_full": self.latex_full
        }


# =============================================================================
# MATH MODE RESULT (Final Output)
# =============================================================================

@dataclass
class MathModeResult(ModeResultBase):
    """
    Complete Math Mode result.
    
    Extends ModeResultBase to include math-specific fields.
    """
    mode: str = "math"
    
    # Math-specific
    intent: Optional[MathIntent] = None
    problem: Optional[Union[MathProblem, DataProblem]] = None
    plan: Optional[SolutionPlan] = None
    result: Optional[MathResult] = None
    validation: Optional[ValidationResult] = None   # From core, NOT redefined
    explanation: Optional[Explanation] = None
    
    # Iterations (OODA loops)
    iterations: int = 0

    # Debate result (adversarial confidence calibration)
    debate: Optional[Dict[str, Any]] = None

    # Human-friendly
    conversation_response: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Full serialization including base and math-specific fields."""
        d = self.to_base_dict()
        d.update({
            "intent": {
                "is_math": self.intent.is_math,
                "confidence": self.intent.confidence,
                "domain": self.intent.domain.value,
                "problem_type": self.intent.problem_type,
            } if self.intent else None,
            "problem": self.problem.to_dict() if self.problem else None,
            "plan": self.plan.to_dict() if self.plan else None,
            "result": self.result.to_dict() if self.result else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "explanation": self.explanation.to_dict() if self.explanation else None,
            "iterations": self.iterations,
            "debate": self.debate,
            "conversation_response": self.conversation_response
        })
        return d


