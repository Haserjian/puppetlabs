"""
Math Mode 3.0 - Research-Grade Reasoning Engine
================================================

Implementation Tiers:
- Tier 1 (Required): SymPy + NumPy/SciPy for algebra, calculus, linear algebra, probability
- Tier 2 (Optional): CVXPY, statsmodels, sklearn, PyTorch, JAX, FEniCS, Lean, Wolfram

This module provides math-specific types only.
Shared types come from quintet.core.
"""

from quintet.math.types import (
    # Intent
    MathDomain,
    MathIntent,
    
    # Expressions
    MathExpression,
    
    # Problems
    MathProblem,
    DataProblem,
    
    # Planning
    Subgoal,
    SolutionPlan,
    
    # Execution
    StepResult,
    MathResult,
    
    # Explanation
    ExplainerMode,
    ExplanationStep,
    Explanation,
    
    # Final Result
    MathModeResult,
)

from quintet.math.math_mode import MathModeOrchestrator, create_math_mode

from quintet.math.llm_integration import (
    # Types
    LLMExplanation,
    RefinedIntent,
    SemanticValidation,

    # Components
    LLMExplainer,
    LLMDetector,
    LLMValidator,

    # Integration
    LLMIntegration,
    create_llm_integration,
)

__all__ = [
    "MathDomain",
    "MathIntent",
    "MathExpression",
    "MathProblem",
    "DataProblem",
    "Subgoal",
    "SolutionPlan",
    "StepResult",
    "MathResult",
    "ExplainerMode",
    "ExplanationStep",
    "Explanation",
    "MathModeResult",
    "MathModeOrchestrator",
    "create_math_mode",

    # LLM Integration
    "LLMExplanation",
    "RefinedIntent",
    "SemanticValidation",
    "LLMExplainer",
    "LLMDetector",
    "LLMValidator",
    "LLMIntegration",
    "create_llm_integration",
]


