"""
Math Mode Orchestrator (Tier 1)
================================

OODA loop orchestrator for Math Mode.
Ties together: Detector → Parser → Planner → Executor → Validator → Explainer

Now includes Constitutional Enforcement:
- Pre-condition checks before execution (treaty compliance for high-stakes math)
- Post-condition checks after execution (temporal ordering, result integrity)
"""

import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from quintet.core.types import (
    Mode, ModeResultBase, ModeError, ErrorCode,
    ContextFlowEntry, CognitionSummary, IncompletenessAssessment,
    WorldImpactAssessment, ColorTile, ColorTileGrid,
    RESOURCE_LIMITS, SPEC_VERSION
)
from quintet.core.council import IntentEnvelope, QuintetSynthesis
from quintet.core.constitutional import (
    ConstitutionalEnforcer, get_enforcer,
    EnforcementResult, ConstitutionalBlockReceipt,
    ConstitutionalViolationReceipt, ConstitutionalPassReceipt
)
from quintet.math.types import (
    MathIntent, MathModeResult, MathDomain, ExplainerMode
)
from quintet.math.detector import MathDetector
from quintet.math.parser import ProblemParser
from quintet.math.planner import SolutionPlanner
from quintet.math.executor import MathExecutor
from quintet.math.validator import MathValidator
from quintet.math.explainer import MathExplainer
from quintet.math.backends.sympy_backend import SymPyBackend
from quintet.math.backends.numeric_backend import NumericBackend
from quintet.math.llm_integration import LLMIntegration, create_llm_integration
from quintet.core.debate import DebateLoop, create_debate_loop, DebateResult, Verdict


class MathModeOrchestrator:
    """
    Main Math Mode orchestrator implementing the OODA loop.
    
    OODA Phases:
    - Observe: Detect math intent, parse problem
    - Orient: Plan solution strategy
    - Decide: Choose backends, verify approach
    - Act: Execute plan, validate, explain
    
    Constitutional Enforcement:
    - Pre-condition check before execution (treaty compliance for high-stakes math)
    - Post-condition check after execution (temporal ordering, result integrity)
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        enforcer: Optional[ConstitutionalEnforcer] = None,
        model_router: Optional[Any] = None,
    ):
        self.config = config or {}
        self.model_router = model_router

        # Initialize backends
        self.backends = {}
        self._init_backends()

        # Initialize components
        self.detector = MathDetector()
        self.parser = ProblemParser()
        self.planner = SolutionPlanner(available_backends=list(self.backends.keys()))
        self.executor = MathExecutor(backends=self.backends)
        self.validator = MathValidator(backends=self.backends)
        self.explainer = MathExplainer()

        # LLM Integration (for enhanced explanations/validation)
        self.llm_integration = create_llm_integration(router=model_router)

        # Debate Loop (for adversarial confidence calibration)
        self.debate_loop = create_debate_loop(
            router=model_router,
            max_rounds=self.config.get("debate_max_rounds", 3)
        )
        self.enable_debate = self.config.get("enable_debate", False)

        # Constitutional enforcer
        self.enforcer = enforcer or get_enforcer(
            strict_mode=self.config.get("strict_mode", False)
        )

        # Iteration limits
        self.max_iterations = self.config.get("max_iterations", 3)

        # Enforcement receipts collected during processing
        self._enforcement_receipts: List[Any] = []

        # Last debate result (if debate was run)
        self._last_debate_result: Optional[DebateResult] = None
    
    def _init_backends(self):
        """Initialize available backends."""
        # Tier 1: Required backends
        sympy = SymPyBackend()
        if sympy.is_available:
            self.backends["sympy"] = sympy
        
        numeric = NumericBackend()
        if numeric.is_available:
            self.backends["numeric"] = numeric
        
        # Tier 2: Optional backends would be initialized here
        # self._init_optional_backends()
    
    @property
    def mode_name(self) -> str:
        return "math"
    
    def detect(
        self,
        query: str,
        synthesis: Optional[Dict[str, Any]] = None
    ) -> MathIntent:
        """
        Detect if query is a math problem.
        
        Returns MathIntent with classification.
        """
        return self.detector.detect(query, synthesis)
    
    def process(
        self,
        query: str,
        synthesis: Optional[Dict[str, Any]] = None,
        intent_envelope: Optional[IntentEnvelope] = None,
        council_synthesis: Optional[QuintetSynthesis] = None,
    ) -> MathModeResult:
        """
        Full OODA loop processing of a math query.
        
        Returns complete MathModeResult.
        """
        start_time = time.time()
        context_flow = []
        errors = []
        
        # ===================
        # OBSERVE: Detect & Parse
        # ===================
        context_flow.append(ContextFlowEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase="observe",
            source="query",
            target="intent",
            influence_type="pattern",
            weight=1.0,
            note="Detecting math intent"
        ))
        
        intent = self.detector.detect(query, synthesis)
        
        if not intent.is_math:
            return self._not_math_result(query, intent, start_time)
        
        context_flow.append(ContextFlowEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase="observe",
            source="intent",
            target="problem",
            influence_type="pattern",
            weight=intent.confidence,
            note=f"Math detected: {intent.domain.value}/{intent.problem_type}"
        ))
        
        problem = self.parser.parse(query, intent, synthesis)

        # Record council guidance if provided
        if council_synthesis:
            context_flow.append(ContextFlowEntry(
                timestamp=datetime.utcnow().isoformat(),
                phase="decide",
                source="quintet_council",
                target="plan",
                influence_type="constraint",
                weight=council_synthesis.confidence,
                note=f"Council decision: {council_synthesis.decision}"
            ))
        if intent_envelope:
            problem.assumptions.append(f"intent:{intent_envelope.intent_id}")
        
        if not problem.parsed_successfully:
            return self._parse_error_result(query, intent, problem, start_time, context_flow)
        
        # ===================
        # ORIENT: Plan
        # ===================
        context_flow.append(ContextFlowEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase="orient",
            source="problem",
            target="plan",
            influence_type="heuristic",
            weight=0.8,
            note="Creating solution plan"
        ))
        
        plan = self.planner.plan(problem)
        
        # Check if we have required backends
        missing = [b for b in plan.backends_required if b not in self.backends]
        if missing:
            return self._missing_backend_result(
                query, intent, problem, plan, missing, start_time, context_flow
            )
        
        # ===================
        # DECIDE: Resource allocation
        # ===================
        resource_limits = RESOURCE_LIMITS.get(intent.compute_tier, RESOURCE_LIMITS["standard"])
        
        context_flow.append(ContextFlowEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase="decide",
            source="plan",
            target="execution",
            influence_type="constraint",
            weight=0.9,
            note=f"Compute tier: {intent.compute_tier}"
        ))
        
        # ===================
        # CONSTITUTIONAL PRE-CHECK
        # ===================
        self._enforcement_receipts = []  # Reset
        
        pre_enforcement = self.enforcer.check_pre_conditions(
            intent=intent_envelope,
            synthesis=council_synthesis,
            context={
                "problem": problem,
                "plan": plan,
                "query": query,
                "mode": "math",
                "domain": intent.domain.value if intent.domain else None
            }
        )
        
        context_flow.append(ContextFlowEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase="decide",
            source="constitutional_enforcer",
            target="execution",
            influence_type="constraint",
            weight=1.0 if pre_enforcement.allowed else 0.0,
            note=f"Pre-check: {'PASS' if pre_enforcement.allowed else 'BLOCKED'} ({len(pre_enforcement.passed_checks)} passed)"
        ))
        
        # If pre-check blocks, return immediately
        if not pre_enforcement.allowed:
            block_receipt = ConstitutionalBlockReceipt(
                invariant_id=pre_enforcement.blocking_invariant.invariant_id if pre_enforcement.blocking_invariant else "",
                invariant_name=pre_enforcement.blocking_invariant.name if pre_enforcement.blocking_invariant else "",
                severity=pre_enforcement.blocking_invariant.severity if pre_enforcement.blocking_invariant else None,
                blocked_action=query,
                block_reason=pre_enforcement.blocking_reason,
                intent_id=intent_envelope.intent_id if intent_envelope else None,
                synthesis_id=council_synthesis.synthesis_id if council_synthesis else None,
                risk_level=council_synthesis.risk_level if council_synthesis else None,
                domain=council_synthesis.world_impact_category if council_synthesis else None
            )
            self._enforcement_receipts.append(block_receipt)
            
            return self._constitutional_block_result(
                query, intent, problem, plan, start_time, context_flow, pre_enforcement
            )
        
        # Log pre-check pass receipt
        if pre_enforcement.passed_checks:
            pass_receipt = ConstitutionalPassReceipt(
                phase="pre",
                invariants_checked=len(pre_enforcement.passed_checks) + len(pre_enforcement.failed_checks),
                invariants_passed=len(pre_enforcement.passed_checks),
                check_time_ms=pre_enforcement.check_time_ms,
                warnings=pre_enforcement.warnings
            )
            self._enforcement_receipts.append(pass_receipt)
        
        # ===================
        # ACT: Execute with iteration loop
        # ===================
        result = None
        validation = None
        iteration = 0
        
        while iteration < self.max_iterations:
            iteration += 1
            
            context_flow.append(ContextFlowEntry(
                timestamp=datetime.utcnow().isoformat(),
                phase="act",
                source="plan",
                target="result",
                influence_type="dependency",
                weight=1.0,
                note=f"Execution iteration {iteration}"
            ))
            
            # Execute
            result = self.executor.execute(plan, problem)
            
            if not result.success:
                # Execution failed - try to recover or give up
                if iteration < self.max_iterations:
                    # Could replan here
                    continue
                break
            
            # Validate
            validation = self.validator.validate(result, problem)
            
            context_flow.append(ContextFlowEntry(
                timestamp=datetime.utcnow().isoformat(),
                phase="verify",
                source="result",
                target="validation",
                influence_type="pattern",
                weight=validation.confidence,
                note=f"Validation: {validation.confidence:.2f} confidence"
            ))
            
            # Check if validation passed
            if validation.valid and validation.confidence >= 0.6:
                break
            
            # Low confidence - could replan/retry
            if iteration < self.max_iterations:
                continue
        
        # ===================
        # DEBATE (Adversarial Confidence Calibration)
        # ===================
        debate_result = None
        self._last_debate_result = None

        if self.enable_debate and result and result.success:
            context_flow.append(ContextFlowEntry(
                timestamp=datetime.utcnow().isoformat(),
                phase="verify",
                source="validation",
                target="debate",
                influence_type="pattern",
                weight=0.9,
                note="Running adversarial debate for confidence calibration"
            ))

            try:
                # Format solution for debate
                solution_str = str(result.final_answer)
                if result.final_answer_latex:
                    solution_str = f"{result.final_answer} (LaTeX: {result.final_answer_latex})"

                debate_result = self.debate_loop.run_sync(
                    problem=query,
                    solution=solution_str,
                    context={"validation_confidence": validation.confidence if validation else 0.5}
                )
                self._last_debate_result = debate_result

                context_flow.append(ContextFlowEntry(
                    timestamp=datetime.utcnow().isoformat(),
                    phase="verify",
                    source="debate",
                    target="confidence",
                    influence_type="pattern",
                    weight=debate_result.confidence,
                    note=f"Debate verdict: {debate_result.verdict.value}, confidence: {debate_result.confidence:.2f}"
                ))

                # Adjust validation confidence based on debate
                if validation and debate_result:
                    # Blend symbolic validation with debate confidence
                    blended_confidence = (validation.confidence * 0.6) + (debate_result.confidence * 0.4)
                    validation.confidence = blended_confidence

            except Exception as e:
                context_flow.append(ContextFlowEntry(
                    timestamp=datetime.utcnow().isoformat(),
                    phase="verify",
                    source="debate",
                    target="error",
                    influence_type="pattern",
                    weight=0.0,
                    note=f"Debate failed: {str(e)}"
                ))

        # ===================
        # EXPLAIN
        # ===================
        explanation = None
        if result and result.success:
            explainer_mode = ExplainerMode.PEDAGOGICAL
            if intent.compute_tier == "deep_search":
                explainer_mode = ExplainerMode.EXPERT

            explanation = self.explainer.explain(
                result, problem, plan,
                options={"mode": explainer_mode}
            )

            # Enhance explanation with LLM if available
            if self.llm_integration.available:
                try:
                    llm_explanation = self.llm_integration.explainer.explain(
                        result={"solution": result.final_answer, "latex": result.final_answer_latex},
                        problem={"query": query, "domain": intent.domain.value if intent.domain else "unknown"},
                        plan={"steps": [str(s) for s in plan.subgoals]} if plan else None
                    )
                    # Merge LLM explanation into existing
                    if llm_explanation.summary:
                        explanation.summary = llm_explanation.summary
                    if llm_explanation.intuition:
                        explanation.intuition = llm_explanation.intuition
                except Exception:
                    pass  # Fall back to basic explanation
        
        # ===================
        # CONSTITUTIONAL POST-CHECK
        # ===================
        # Build temporary result for post-condition check
        temp_result = MathModeResult(
            mode="math",
            success=result.success if result else False,
            context_flow=context_flow,
            world_impact=self._assess_world_impact(problem, intent)
        )
        
        post_enforcement = self.enforcer.check_post_conditions(
            result=temp_result,
            context={
                "problem": problem,
                "plan": plan,
                "validation": validation,
                "mode": "math"
            }
        )
        
        context_flow.append(ContextFlowEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase="verify",
            source="constitutional_enforcer",
            target="result",
            influence_type="pattern",
            weight=1.0 if post_enforcement.allowed else 0.5,
            note=f"Post-check: {'PASS' if post_enforcement.allowed else 'VIOLATION'} ({len(post_enforcement.passed_checks)} passed)"
        ))
        
        # Log any post-check violations
        post_enforcement_errors = []
        if not post_enforcement.allowed:
            violation_receipt = ConstitutionalViolationReceipt(
                invariant_id=post_enforcement.blocking_invariant.invariant_id if post_enforcement.blocking_invariant else "",
                invariant_name=post_enforcement.blocking_invariant.name if post_enforcement.blocking_invariant else "",
                severity=post_enforcement.blocking_invariant.severity if post_enforcement.blocking_invariant else None,
                violation_description=post_enforcement.blocking_reason,
                escalated_to_guardian=True
            )
            self._enforcement_receipts.append(violation_receipt)
            
            for warning in post_enforcement.warnings:
                post_enforcement_errors.append(ModeError(
                    code=ErrorCode.VERIFICATION_FAILED,
                    stage="verify",
                    message=warning,
                    recoverable=False,
                    organism_action="warn"
                ))
        else:
            pass_receipt = ConstitutionalPassReceipt(
                phase="post",
                invariants_checked=len(post_enforcement.passed_checks) + len(post_enforcement.failed_checks),
                invariants_passed=len(post_enforcement.passed_checks),
                check_time_ms=post_enforcement.check_time_ms,
                warnings=post_enforcement.warnings
            )
            self._enforcement_receipts.append(pass_receipt)
        
        # ===================
        # Build final result
        # ===================
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Ensure minimal flow metadata for UI/receipts
        if not context_flow:
            context_flow.append(ContextFlowEntry(
                timestamp=datetime.utcnow().isoformat(),
                phase="observe",
                source="math_mode",
                target="problem",
                influence_type="pattern",
                weight=0.4,
                note="Auto-seeded flow entry"
            ))

        # Build cognition summary
        cognition = CognitionSummary(
            observed=f"Math problem: {intent.domain.value} / {intent.problem_type}",
            oriented=f"Planned {len(plan.subgoals)} steps using {', '.join(plan.backends_required)}",
            acted=f"Executed in {iteration} iteration(s), confidence: {validation.confidence:.2f}" if validation else "Execution failed",
            key_decision=f"Used {plan.backends_required[0] if plan.backends_required else 'default'} as primary solver",
            confidence_rationale=self._confidence_rationale(validation) if validation else "No validation performed"
        )
        
        # Build incompleteness assessment
        incompleteness = self._assess_incompleteness(result, validation)
        
        # Build world impact assessment
        world_impact = self._assess_world_impact(problem, intent)
        
        # Build color tiles
        color_tiles = self._build_color_tiles(intent, result, validation)
        
        # Build conversation response
        conversation_response = self._build_response(result, explanation, validation)
        
        # Combine execution errors with post-enforcement errors
        all_errors = [ModeError(
            code=ErrorCode.EXECUTION_ERROR,
            stage="execute",
            message=e,
            recoverable=False
        ) for e in (result.errors if result else [])]
        all_errors.extend(post_enforcement_errors)
        
        # Build debate summary for result
        debate_summary = None
        if debate_result:
            debate_summary = {
                "debate_id": debate_result.debate_id,
                "verdict": debate_result.verdict.value,
                "confidence": debate_result.confidence,
                "proposer_won": debate_result.proposer_won,
                "rounds_completed": debate_result.rounds_completed,
                "judge_reasoning": debate_result.judge_reasoning,
                "duration_ms": debate_result.duration_ms,
            }

        return MathModeResult(
            result_id=str(uuid.uuid4()),
            spec_version=SPEC_VERSION,
            mode="math",
            success=(result.success if result else False) and post_enforcement.allowed,
            errors=all_errors,
            context_flow=context_flow,
            color_tiles=color_tiles,
            cognition_summary=cognition,
            incompleteness=incompleteness,
            world_impact=world_impact,
            total_time_ms=elapsed_ms,
            intent=intent,
            problem=problem,
            plan=plan,
            result=result,
            validation=validation,
            explanation=explanation,
            iterations=iteration,
            debate=debate_summary,
            conversation_response=conversation_response
        )
    
    def _not_math_result(
        self,
        query: str,
        intent: MathIntent,
        start_time: float
    ) -> MathModeResult:
        """Return result for non-math query."""
        elapsed = (time.time() - start_time) * 1000
        
        return MathModeResult(
            success=False,
            mode="math",
            errors=[ModeError(
                code=ErrorCode.INTENT_UNCLEAR,
                stage="detect",
                message="Query does not appear to be a math problem",
                recoverable=True,
                suggested_action="Try Build Mode instead"
            )],
            total_time_ms=elapsed,
            intent=intent,
            conversation_response="This doesn't appear to be a math problem. Can you rephrase or try a different query?"
        )
    
    def _parse_error_result(
        self,
        query: str,
        intent: MathIntent,
        problem,
        start_time: float,
        context_flow
    ) -> MathModeResult:
        """Return result for parse failure."""
        elapsed = (time.time() - start_time) * 1000
        
        return MathModeResult(
            success=False,
            mode="math",
            errors=[ModeError(
                code=ErrorCode.PARSE_ERROR,
                stage="parse",
                message="Could not parse the mathematical expressions",
                recoverable=True,
                suggested_action="Check syntax and try again"
            )],
            context_flow=context_flow,
            total_time_ms=elapsed,
            intent=intent,
            problem=problem,
            conversation_response="I had trouble understanding the mathematical expressions. Could you rephrase?"
        )
    
    def _missing_backend_result(
        self,
        query: str,
        intent: MathIntent,
        problem,
        plan,
        missing: list,
        start_time: float,
        context_flow
    ) -> MathModeResult:
        """Return result for missing backends."""
        elapsed = (time.time() - start_time) * 1000
        
        return MathModeResult(
            success=False,
            mode="math",
            errors=[ModeError(
                code=ErrorCode.BACKEND_UNAVAILABLE,
                stage="plan",
                message=f"Required backends not available: {', '.join(missing)}",
                recoverable=False,
                suggested_action=f"Install: {', '.join(missing)}"
            )],
            context_flow=context_flow,
            total_time_ms=elapsed,
            intent=intent,
            problem=problem,
            plan=plan,
            conversation_response=f"This problem requires backends that aren't available: {', '.join(missing)}"
        )
    
    def _constitutional_block_result(
        self,
        query: str,
        intent: MathIntent,
        problem,
        plan,
        start_time: float,
        context_flow,
        enforcement: EnforcementResult
    ) -> MathModeResult:
        """Return result when constitutional pre-check blocks execution."""
        elapsed = (time.time() - start_time) * 1000
        
        blocking_inv = enforcement.blocking_invariant
        inv_name = blocking_inv.name if blocking_inv else "Unknown"
        
        return MathModeResult(
            success=False,
            mode="math",
            errors=[ModeError(
                code=ErrorCode.WORLD_IMPACT_BLOCKED,
                stage="decide",
                message=f"Constitutional pre-check blocked: {inv_name}",
                recoverable=True,
                details={
                    "invariant_id": blocking_inv.invariant_id if blocking_inv else None,
                    "reason": enforcement.blocking_reason,
                    "passed_checks": enforcement.passed_checks,
                    "failed_checks": enforcement.failed_checks
                },
                suggested_action=f"Ensure compliance with {inv_name} before proceeding",
                organism_action="block"
            )],
            context_flow=context_flow,
            total_time_ms=elapsed,
            intent=intent,
            problem=problem,
            plan=plan,
            conversation_response=f"⚠️ **Constitutional Block**: This math problem was blocked by the `{inv_name}` invariant.\n\n**Reason:** {enforcement.blocking_reason}\n\nPlease provide a treaty or ensure compliance before retrying."
        )
    
    def _confidence_rationale(self, validation) -> str:
        """Build rationale for confidence level."""
        if validation.confidence >= 0.9:
            return "High confidence: multiple verification methods passed"
        elif validation.confidence >= 0.7:
            return "Good confidence: core verifications passed"
        elif validation.confidence >= 0.5:
            return "Moderate confidence: some checks passed"
        else:
            return "Low confidence: verification incomplete"
    
    def _assess_incompleteness(self, result, validation) -> IncompletenessAssessment:
        """Assess solution completeness."""
        if not result or not result.success:
            return IncompletenessAssessment(
                score=0.0,
                missing_elements=["Solution"],
                next_steps=["Review input and retry"]
            )
        
        score = validation.confidence if validation else 0.5
        missing = []
        partial = []
        next_steps = []
        
        if validation and not validation.valid:
            missing.append("Verified solution")
            next_steps.append("Re-solve with alternative method")
        
        if validation and validation.suggested_review:
            partial.append("Solution confidence")
            next_steps.append("Manual verification recommended")
        
        return IncompletenessAssessment(
            score=score,
            missing_elements=missing,
            partial_elements=partial,
            next_steps=next_steps
        )
    
    def _assess_world_impact(self, problem, intent) -> WorldImpactAssessment:
        """Assess world impact of the problem."""
        # Simple heuristic based on domain
        high_impact_domains = {
            MathDomain.STATISTICS: "Data analysis may influence decisions",
            MathDomain.OPTIMIZATION: "Optimization affects resource allocation",
            MathDomain.MACHINE_LEARNING: "ML models can have broad impact"
        }
        
        category = None
        impact_score = 0.0
        
        if problem.domain in high_impact_domains:
            category = "decision_support"
            impact_score = 0.3
        
        return WorldImpactAssessment(
            category=category,
            impact_score=impact_score,
            verification_tier="standard" if impact_score < 0.5 else "elevated"
        )
    
    def _build_color_tiles(self, intent, result, validation) -> ColorTileGrid:
        """Build 3x3 color tile grid."""
        tiles = []
        
        # Row A: Observation
        tiles.append(ColorTile(
            tile_id="A1",
            color="#4CAF50" if intent.is_math else "#F44336",
            mood="confident" if intent.confidence > 0.7 else "uncertain",
            signal="success" if intent.is_math else "warning",
            tagline="Math Found" if intent.is_math else "Not Math",
            value=intent.confidence
        ))
        tiles.append(ColorTile(
            tile_id="A2",
            color=self._domain_color(intent.domain),
            mood="confident",
            signal="success",
            tagline=intent.domain.value[:10].title()
        ))
        tiles.append(ColorTile(
            tile_id="A3",
            color="#2196F3",
            mood="confident",
            signal="success",
            tagline=intent.problem_type[:10].title()
        ))
        
        # Row B: Orientation/Action
        if result:
            tiles.append(ColorTile(
                tile_id="B1",
                color="#4CAF50" if result.success else "#F44336",
                mood="satisfied" if result.success else "alert",
                signal="success" if result.success else "error",
                tagline="Solved" if result.success else "Failed"
            ))
        else:
            tiles.append(ColorTile(
                tile_id="B1",
                color="#9E9E9E",
                mood="uncertain",
                signal="waiting",
                tagline="Pending"
            ))
        
        tiles.append(ColorTile(
            tile_id="B2",
            color="#FF9800",
            mood="confident",
            signal="success",
            tagline=f"{len(result.step_results) if result else 0} Steps"
        ))
        
        # Validation tile
        if validation:
            val_color = "#4CAF50" if validation.valid else "#F44336"
            val_mood = "satisfied" if validation.valid else "alert"
            tiles.append(ColorTile(
                tile_id="B3",
                color=val_color,
                mood=val_mood,
                signal="success" if validation.valid else "warning",
                tagline=f"{validation.confidence:.0%} Conf",
                value=validation.confidence
            ))
        else:
            tiles.append(ColorTile(
                tile_id="B3",
                color="#9E9E9E",
                mood="uncertain",
                signal="waiting",
                tagline="No Valid"
            ))
        
        # Row C: Meta
        tiles.append(ColorTile(
            tile_id="C1",
            color="#9C27B0",
            mood="confident",
            signal="success",
            tagline=intent.compute_tier[:10].title()
        ))
        tiles.append(ColorTile(
            tile_id="C2",
            color="#00BCD4",
            mood="confident",
            signal="success",
            tagline="Tier 1"
        ))
        tiles.append(ColorTile(
            tile_id="C3",
            color="#607D8B",
            mood="confident",
            signal="success",
            tagline="Complete"
        ))
        
        return ColorTileGrid(
            grid_id=str(uuid.uuid4()),
            mode="math",
            tiles=tiles
        )
    
    def _domain_color(self, domain: MathDomain) -> str:
        """Get color for domain."""
        colors = {
            MathDomain.ALGEBRA: "#E91E63",
            MathDomain.CALCULUS: "#9C27B0",
            MathDomain.LINEAR_ALGEBRA: "#673AB7",
            MathDomain.PROBABILITY: "#3F51B5",
            MathDomain.NUMBER_THEORY: "#2196F3",
            MathDomain.OPTIMIZATION: "#009688",
            MathDomain.STATISTICS: "#4CAF50",
            MathDomain.DIFFERENTIAL_EQUATIONS: "#FF5722",
            MathDomain.MACHINE_LEARNING: "#795548",
            MathDomain.PDE: "#607D8B",
            MathDomain.FORMAL: "#9E9E9E"
        }
        return colors.get(domain, "#757575")
    
    def _build_response(self, result, explanation, validation) -> str:
        """Build human-friendly response."""
        if not result or not result.success:
            return "I couldn't solve this problem. Please check the input and try again."
        
        response = []
        
        # Add solution
        response.append(f"**Solution:** {result.final_answer}")
        
        # Add LaTeX if available
        if result.final_answer_latex:
            response.append(f"\n$$\n{result.final_answer_latex}\n$$")
        
        # Add confidence
        if validation:
            response.append(f"\n**Confidence:** {validation.confidence:.0%}")
        
        # Add brief explanation
        if explanation and explanation.summary:
            response.append(f"\n{explanation.summary}")
        
        return "\n".join(response)


    def process_with_synthesis(
        self,
        intent_envelope: IntentEnvelope,
        council_synthesis: QuintetSynthesis,
        query: str,
        synthesis: Optional[Dict[str, Any]] = None,
    ) -> MathModeResult:
        """
        Convenience wrapper that threads the council synthesis/intent through.
        """
        return self.process(
            query=query,
            synthesis=synthesis,
            intent_envelope=intent_envelope,
            council_synthesis=council_synthesis,
        )


# Convenience function
def create_math_mode(config: Optional[Dict[str, Any]] = None) -> MathModeOrchestrator:
    """Create and return a configured MathModeOrchestrator."""
    return MathModeOrchestrator(config)

