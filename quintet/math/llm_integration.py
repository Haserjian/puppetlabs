"""
LLM Integration Layer for Math Mode

Bridges Math Mode with Model Fabric, enabling:
- LLM-powered explanations of solutions
- LLM-assisted intent detection for ambiguous queries
- LLM semantic validation of mathematical results

This module wires the existing Math Mode components to actual LLM calls
via the Model Fabric's slot-based routing system.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from quintet.model.router import ModelRouter
    from quintet.model.types import ModelResponse


@dataclass
class LLMExplanation:
    """Structured explanation from LLM."""

    summary: str
    steps: List[str]
    intuition: str
    caveats: List[str] = field(default_factory=list)
    confidence: float = 0.8

    def to_markdown(self) -> str:
        """Render as markdown."""
        lines = [
            f"## Summary\n{self.summary}",
            "\n## Steps",
        ]
        for i, step in enumerate(self.steps, 1):
            lines.append(f"{i}. {step}")
        lines.append(f"\n## Intuition\n{self.intuition}")
        if self.caveats:
            lines.append("\n## Caveats")
            for caveat in self.caveats:
                lines.append(f"- {caveat}")
        return "\n".join(lines)


@dataclass
class RefinedIntent:
    """Refined intent detection from LLM."""

    domain: str  # "algebra", "calculus", "linear_algebra", "statistics", "unknown"
    confidence: float
    interpretation: str  # How LLM interpreted the query
    ambiguities: List[str] = field(default_factory=list)
    suggested_reformulation: Optional[str] = None


@dataclass
class SemanticValidation:
    """Semantic validation result from LLM."""

    is_valid: bool
    reasoning: str
    potential_issues: List[str] = field(default_factory=list)
    alternative_solutions: List[str] = field(default_factory=list)
    confidence: float = 0.8


class LLMExplainer:
    """
    LLM-powered explanation generator for mathematical solutions.

    Uses the 'math_helper' slot from Model Fabric to generate
    human-readable explanations of solution steps.
    """

    SLOT = "math_helper"

    def __init__(self, router: Optional["ModelRouter"] = None):
        self.router = router
        self._available = router is not None

    @property
    def available(self) -> bool:
        return self._available and self.router is not None

    def explain(
        self,
        result: Dict[str, Any],
        problem: Dict[str, Any],
        plan: Optional[Dict[str, Any]] = None,
    ) -> LLMExplanation:
        """
        Generate explanation synchronously.

        Falls back to basic explanation if LLM unavailable.
        """
        if not self.available:
            return self._fallback_explanation(result, problem)

        try:
            return asyncio.get_event_loop().run_until_complete(
                self.explain_async(result, problem, plan)
            )
        except RuntimeError:
            # No event loop running
            return self._fallback_explanation(result, problem)

    async def explain_async(
        self,
        result: Dict[str, Any],
        problem: Dict[str, Any],
        plan: Optional[Dict[str, Any]] = None,
    ) -> LLMExplanation:
        """Generate explanation using LLM."""
        if not self.available:
            return self._fallback_explanation(result, problem)

        prompt = self._build_explanation_prompt(result, problem, plan)

        response = await self.router.call_async(
            slot=self.SLOT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for factual explanation
        )

        return self._parse_explanation_response(response, result, problem)

    def _build_explanation_prompt(
        self,
        result: Dict[str, Any],
        problem: Dict[str, Any],
        plan: Optional[Dict[str, Any]],
    ) -> str:
        """Build prompt for explanation generation."""
        query = problem.get("query", problem.get("raw_query", "Unknown problem"))
        solution = result.get("solution", result.get("result", "Unknown solution"))

        prompt = f"""Explain this mathematical solution clearly and pedagogically.

**Problem**: {query}

**Solution**: {solution}

"""
        if plan:
            steps = plan.get("steps", plan.get("subgoals", []))
            if steps:
                prompt += "**Solution Steps**:\n"
                for i, step in enumerate(steps, 1):
                    step_desc = step if isinstance(step, str) else step.get("description", str(step))
                    prompt += f"{i}. {step_desc}\n"
                prompt += "\n"

        prompt += """Provide:
1. A brief summary (1-2 sentences)
2. Step-by-step explanation
3. Intuitive understanding (why this works)
4. Any caveats or edge cases

Format your response as:
SUMMARY: <summary>
STEPS:
- <step 1>
- <step 2>
...
INTUITION: <intuition>
CAVEATS:
- <caveat 1> (if any)
"""
        return prompt

    def _parse_explanation_response(
        self,
        response: "ModelResponse",
        result: Dict[str, Any],
        problem: Dict[str, Any],
    ) -> LLMExplanation:
        """Parse LLM response into structured explanation."""
        content = response.content if hasattr(response, 'content') else str(response)

        # Parse sections
        summary = ""
        steps = []
        intuition = ""
        caveats = []

        current_section = None
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("SUMMARY:"):
                summary = line[8:].strip()
                current_section = "summary"
            elif line.startswith("STEPS:"):
                current_section = "steps"
            elif line.startswith("INTUITION:"):
                intuition = line[10:].strip()
                current_section = "intuition"
            elif line.startswith("CAVEATS:"):
                current_section = "caveats"
            elif line.startswith("- ") and current_section == "steps":
                steps.append(line[2:])
            elif line.startswith("- ") and current_section == "caveats":
                caveats.append(line[2:])
            elif current_section == "summary" and not summary:
                summary = line
            elif current_section == "intuition" and not intuition:
                intuition = line

        # Fallback if parsing failed
        if not summary:
            summary = f"Solution to: {problem.get('query', 'the problem')}"
        if not steps:
            steps = [f"Result: {result.get('solution', 'computed')}"]
        if not intuition:
            intuition = "Standard mathematical techniques applied."

        return LLMExplanation(
            summary=summary,
            steps=steps,
            intuition=intuition,
            caveats=caveats,
            confidence=0.85,
        )

    def _fallback_explanation(
        self,
        result: Dict[str, Any],
        problem: Dict[str, Any],
    ) -> LLMExplanation:
        """Generate basic explanation without LLM."""
        query = problem.get("query", problem.get("raw_query", "Unknown"))
        solution = result.get("solution", result.get("result", "Unknown"))

        return LLMExplanation(
            summary=f"Solved: {query}",
            steps=[f"Computed result: {solution}"],
            intuition="Solution obtained via symbolic computation.",
            caveats=["LLM explanation unavailable - basic summary only."],
            confidence=0.5,
        )


class LLMDetector:
    """
    LLM-assisted intent detection for ambiguous queries.

    When heuristic detection is uncertain, uses LLM to
    interpret the mathematical domain and intent.
    """

    SLOT = "math_helper"
    UNCERTAINTY_THRESHOLD = 0.6  # Below this, consult LLM

    def __init__(self, router: Optional["ModelRouter"] = None):
        self.router = router
        self._available = router is not None

    @property
    def available(self) -> bool:
        return self._available and self.router is not None

    def refine_detection(
        self,
        query: str,
        heuristic_result: Dict[str, Any],
    ) -> RefinedIntent:
        """Refine detection synchronously."""
        if not self.available:
            return self._from_heuristic(heuristic_result)

        # Only consult LLM if heuristic is uncertain
        confidence = heuristic_result.get("confidence", 0)
        if confidence >= self.UNCERTAINTY_THRESHOLD:
            return self._from_heuristic(heuristic_result)

        try:
            return asyncio.get_event_loop().run_until_complete(
                self.refine_detection_async(query, heuristic_result)
            )
        except RuntimeError:
            return self._from_heuristic(heuristic_result)

    async def refine_detection_async(
        self,
        query: str,
        heuristic_result: Dict[str, Any],
    ) -> RefinedIntent:
        """Refine detection using LLM."""
        if not self.available:
            return self._from_heuristic(heuristic_result)

        confidence = heuristic_result.get("confidence", 0)
        if confidence >= self.UNCERTAINTY_THRESHOLD:
            return self._from_heuristic(heuristic_result)

        prompt = f"""Classify this mathematical query:

Query: "{query}"

What mathematical domain does this belong to?
- algebra (equations, polynomials, factoring)
- calculus (derivatives, integrals, limits)
- linear_algebra (matrices, vectors, systems)
- statistics (probability, distributions, hypothesis testing)
- unknown (not clearly mathematical)

Also identify any ambiguities in the query.

Respond in format:
DOMAIN: <domain>
CONFIDENCE: <0.0-1.0>
INTERPRETATION: <how you understand the query>
AMBIGUITIES: <comma-separated list, or "none">
REFORMULATION: <clearer version of the query, or "none">
"""

        response = await self.router.call_async(
            slot=self.SLOT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        return self._parse_detection_response(response, query, heuristic_result)

    def _parse_detection_response(
        self,
        response: "ModelResponse",
        query: str,
        heuristic_result: Dict[str, Any],
    ) -> RefinedIntent:
        """Parse LLM response into refined intent."""
        content = response.content if hasattr(response, 'content') else str(response)

        domain = "unknown"
        confidence = 0.5
        interpretation = query
        ambiguities = []
        reformulation = None

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("DOMAIN:"):
                domain = line[7:].strip().lower()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line[11:].strip())
                except ValueError:
                    pass
            elif line.startswith("INTERPRETATION:"):
                interpretation = line[15:].strip()
            elif line.startswith("AMBIGUITIES:"):
                amb = line[12:].strip()
                if amb.lower() != "none":
                    ambiguities = [a.strip() for a in amb.split(",")]
            elif line.startswith("REFORMULATION:"):
                ref = line[14:].strip()
                if ref.lower() != "none":
                    reformulation = ref

        return RefinedIntent(
            domain=domain,
            confidence=confidence,
            interpretation=interpretation,
            ambiguities=ambiguities,
            suggested_reformulation=reformulation,
        )

    def _from_heuristic(self, heuristic_result: Dict[str, Any]) -> RefinedIntent:
        """Convert heuristic result to RefinedIntent."""
        return RefinedIntent(
            domain=heuristic_result.get("domain", "unknown"),
            confidence=heuristic_result.get("confidence", 0.5),
            interpretation=heuristic_result.get("query", ""),
            ambiguities=[],
            suggested_reformulation=None,
        )


class LLMValidator:
    """
    LLM-powered semantic validation of mathematical results.

    Goes beyond syntactic validation (substitution checks) to
    assess whether the solution makes semantic sense.
    """

    SLOT = "math_helper"

    def __init__(self, router: Optional["ModelRouter"] = None):
        self.router = router
        self._available = router is not None

    @property
    def available(self) -> bool:
        return self._available and self.router is not None

    def validate(
        self,
        problem: Dict[str, Any],
        result: Dict[str, Any],
        symbolic_validation: Optional[Dict[str, Any]] = None,
    ) -> SemanticValidation:
        """Validate synchronously."""
        if not self.available:
            return self._fallback_validation(symbolic_validation)

        try:
            return asyncio.get_event_loop().run_until_complete(
                self.validate_async(problem, result, symbolic_validation)
            )
        except RuntimeError:
            return self._fallback_validation(symbolic_validation)

    async def validate_async(
        self,
        problem: Dict[str, Any],
        result: Dict[str, Any],
        symbolic_validation: Optional[Dict[str, Any]] = None,
    ) -> SemanticValidation:
        """Validate using LLM."""
        if not self.available:
            return self._fallback_validation(symbolic_validation)

        query = problem.get("query", problem.get("raw_query", ""))
        solution = result.get("solution", result.get("result", ""))

        prompt = f"""Validate this mathematical solution:

**Problem**: {query}
**Solution**: {solution}

"""
        if symbolic_validation:
            sym_valid = symbolic_validation.get("is_valid", "unknown")
            prompt += f"**Symbolic check**: {sym_valid}\n"

        prompt += """
Assess:
1. Is the solution mathematically correct?
2. Does it fully answer the question?
3. Are there edge cases or alternative interpretations?

Respond in format:
VALID: <yes/no>
REASONING: <explanation>
ISSUES: <comma-separated list, or "none">
ALTERNATIVES: <comma-separated alternative solutions, or "none">
CONFIDENCE: <0.0-1.0>
"""

        response = await self.router.call_async(
            slot=self.SLOT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        return self._parse_validation_response(response, symbolic_validation)

    def _parse_validation_response(
        self,
        response: "ModelResponse",
        symbolic_validation: Optional[Dict[str, Any]],
    ) -> SemanticValidation:
        """Parse LLM response into validation result."""
        content = response.content if hasattr(response, 'content') else str(response)

        is_valid = True
        reasoning = ""
        issues = []
        alternatives = []
        confidence = 0.7

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("VALID:"):
                is_valid = line[6:].strip().lower() in ("yes", "true", "1")
            elif line.startswith("REASONING:"):
                reasoning = line[10:].strip()
            elif line.startswith("ISSUES:"):
                iss = line[7:].strip()
                if iss.lower() != "none":
                    issues = [i.strip() for i in iss.split(",")]
            elif line.startswith("ALTERNATIVES:"):
                alt = line[13:].strip()
                if alt.lower() != "none":
                    alternatives = [a.strip() for a in alt.split(",")]
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line[11:].strip())
                except ValueError:
                    pass

        # Combine with symbolic validation
        if symbolic_validation and not symbolic_validation.get("is_valid", True):
            is_valid = False
            issues.insert(0, "Failed symbolic validation")

        return SemanticValidation(
            is_valid=is_valid,
            reasoning=reasoning or "Validation complete.",
            potential_issues=issues,
            alternative_solutions=alternatives,
            confidence=confidence,
        )

    def _fallback_validation(
        self,
        symbolic_validation: Optional[Dict[str, Any]],
    ) -> SemanticValidation:
        """Return validation based only on symbolic check."""
        if symbolic_validation:
            return SemanticValidation(
                is_valid=symbolic_validation.get("is_valid", True),
                reasoning="Based on symbolic validation only (LLM unavailable).",
                potential_issues=[],
                alternative_solutions=[],
                confidence=0.6,
            )
        return SemanticValidation(
            is_valid=True,
            reasoning="No validation performed (LLM unavailable).",
            potential_issues=["Validation skipped"],
            alternative_solutions=[],
            confidence=0.3,
        )


@dataclass
class LLMIntegration:
    """
    Unified LLM integration for Math Mode.

    Bundles explainer, detector, and validator with shared router.
    """

    explainer: LLMExplainer
    detector: LLMDetector
    validator: LLMValidator
    router: Optional["ModelRouter"] = None

    @classmethod
    def create(cls, router: Optional["ModelRouter"] = None) -> "LLMIntegration":
        """Create integration with shared router."""
        return cls(
            explainer=LLMExplainer(router),
            detector=LLMDetector(router),
            validator=LLMValidator(router),
            router=router,
        )

    @property
    def available(self) -> bool:
        """Check if any LLM features are available."""
        return self.router is not None


# Convenience factory
def create_llm_integration(router: Optional["ModelRouter"] = None) -> LLMIntegration:
    """Create LLM integration layer."""
    return LLMIntegration.create(router)
