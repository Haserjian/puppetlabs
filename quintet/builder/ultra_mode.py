"""
Ultra Mode Orchestrator (Build Mode)
=====================================

OODA loop orchestrator for Build Mode.
Ties together: Detector → SpecGenerator → Executor → Validation

Now includes Constitutional Enforcement:
- Pre-condition checks before execution (treaty compliance, etc.)
- Post-condition checks after execution (temporal ordering, dignity floor, etc.)
"""

import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Callable, List

from quintet.core.types import (
    Mode, ModeResultBase, ModeError, ErrorCode,
    ContextFlowEntry, CognitionSummary, IncompletenessAssessment,
    WorldImpactAssessment, ColorTile, ColorTileGrid,
    SPEC_VERSION
)
from quintet.core.council import IntentEnvelope, QuintetSynthesis
from quintet.core.constitutional import (
    ConstitutionalEnforcer, get_enforcer,
    EnforcementResult, ConstitutionalBlockReceipt,
    ConstitutionalViolationReceipt, ConstitutionalPassReceipt
)
from quintet.builder.types import (
    BuildIntent, BuildCategory, ProjectBlueprint, BuildResult
)
from quintet.builder.detector import BuilderDetector
from quintet.builder.specification import SpecGenerator
from quintet.builder.executor import BuilderExecutor


class UltraModeOrchestrator:
    """
    Main Build Mode orchestrator implementing the OODA loop.
    
    OODA Phases:
    - Observe: Detect build intent
    - Orient: Scan project context, generate blueprint
    - Decide: (Optional) await approval via hook
    - Act: Execute blueprint, validate output
    
    Constitutional Enforcement:
    - Pre-condition check before execution (treaty compliance, etc.)
    - Post-condition check after execution (temporal, dignity, etc.)
    """
    
    def __init__(
        self,
        project_root: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        on_blueprint_ready: Optional[Callable[[ProjectBlueprint], bool]] = None,
        on_error: Optional[Callable[[str], Optional[str]]] = None,
        enforcer: Optional[ConstitutionalEnforcer] = None
    ):
        self.project_root = project_root
        self.config = config or {}
        self.on_blueprint_ready = on_blueprint_ready  # Returns True to proceed
        self.on_error = on_error  # Returns correction hint or None
        
        # Initialize components
        self.detector = BuilderDetector()
        self.spec_generator = SpecGenerator(project_root)
        self.executor = BuilderExecutor(
            project_root=project_root,
            dry_run=self.config.get("dry_run", False),
            enable_rollback=self.config.get("enable_rollback", True)
        )
        
        # Constitutional enforcer
        self.enforcer = enforcer or get_enforcer(
            strict_mode=self.config.get("strict_mode", False)
        )
        
        # Iteration limits
        self.max_retries = self.config.get("max_retries", 2)
        
        # Enforcement receipts collected during processing
        self._enforcement_receipts: List[Any] = []
    
    @property
    def mode_name(self) -> str:
        return "build"
    
    def detect(
        self,
        query: str,
        synthesis: Optional[Dict[str, Any]] = None
    ) -> BuildIntent:
        """
        Detect if query is a build request.
        
        Returns BuildIntent with classification.
        """
        return self.detector.detect(query, synthesis)
    
    def process(
        self,
        query: str,
        synthesis: Optional[Dict[str, Any]] = None,
        intent_envelope: Optional[IntentEnvelope] = None,
        council_synthesis: Optional[QuintetSynthesis] = None,
    ) -> BuildResult:
        """
        Full OODA loop processing of a build query.
        
        Returns complete BuildResult.
        """
        start_time = time.time()
        context_flow = []
        errors = []
        
        # ===================
        # OBSERVE: Detect Intent
        # ===================
        context_flow.append(ContextFlowEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase="observe",
            source="query",
            target="intent",
            influence_type="pattern",
            weight=1.0,
            note="Detecting build intent"
        ))
        
        intent = self.detector.detect(query, synthesis)
        
        if not intent.is_build:
            return self._not_build_result(query, intent, start_time)
        
        context_flow.append(ContextFlowEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase="observe",
            source="intent",
            target="context",
            influence_type="pattern",
            weight=intent.confidence,
            note=f"Build detected: {intent.category.value}"
        ))
        
        # ===================
        # ORIENT: Scan Context & Generate Blueprint
        # ===================
        context_flow.append(ContextFlowEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase="orient",
            source="project",
            target="context",
            influence_type="dependency",
            weight=0.8,
            note="Scanning project context"
        ))
        
        project_context = self.spec_generator.scan_project()
        
        context_flow.append(ContextFlowEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase="orient",
            source="context",
            target="blueprint",
            influence_type="heuristic",
            weight=0.9,
            note="Generating blueprint"
        ))
        
        blueprint = self.spec_generator.generate_blueprint(intent, project_context, synthesis)

        # Inject council synthesis / intent metadata into flow if provided
        if council_synthesis:
            blueprint.context_flow.append(
                ContextFlowEntry(
                    timestamp=datetime.utcnow().isoformat(),
                    phase="decide",
                    source="quintet_council",
                    target="blueprint",
                    influence_type="constraint",
                    weight=council_synthesis.confidence,
                    note=f"Council decision: {council_synthesis.decision}"
                )
            )
        if intent_envelope:
            blueprint.recursion_seeds.append(f"intent:{intent_envelope.intent_id}")
        
        # ===================
        # DECIDE: Optional Approval Hook
        # ===================
        if self.on_blueprint_ready:
            context_flow.append(ContextFlowEntry(
                timestamp=datetime.utcnow().isoformat(),
                phase="decide",
                source="blueprint",
                target="approval",
                influence_type="constraint",
                weight=1.0,
                note="Awaiting approval"
            ))
            
            approved = self.on_blueprint_ready(blueprint)
            if not approved:
                return self._approval_denied_result(
                    query, intent, blueprint, start_time, context_flow
                )
            
            blueprint.approved = True
        else:
            # Auto-approve if no hook
            blueprint.approved = True
        
        # ===================
        # CONSTITUTIONAL PRE-CHECK
        # ===================
        self._enforcement_receipts = []  # Reset
        
        pre_enforcement = self.enforcer.check_pre_conditions(
            intent=intent_envelope,
            synthesis=council_synthesis,
            context={
                "blueprint": blueprint,
                "query": query,
                "mode": "build"
            }
        )
        
        context_flow.append(ContextFlowEntry(
            timestamp=datetime.utcnow().isoformat(),
            phase="decide",
            source="constitutional_enforcer",
            target="execution",
            influence_type="constraint",
            weight=1.0 if pre_enforcement.allowed else 0.0,
            note=f"Pre-check: {'PASS' if pre_enforcement.allowed else 'BLOCKED'} ({len(pre_enforcement.passed_checks)} passed, {len(pre_enforcement.failed_checks)} failed)"
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
                query, intent, blueprint, start_time, context_flow, pre_enforcement
            )
        
        # Log pre-check pass receipt for audit
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
        # ACT: Execute with Retry Loop
        # ===================
        file_results = []
        command_results = []
        validation = None
        iteration = 0
        
        while iteration < self.max_retries:
            iteration += 1
            
            context_flow.append(ContextFlowEntry(
                timestamp=datetime.utcnow().isoformat(),
                phase="act",
                source="blueprint",
                target="execution",
                influence_type="dependency",
                weight=1.0,
                note=f"Execution iteration {iteration}"
            ))
            
            # Execute
            file_results, command_results, validation = self.executor.execute(blueprint)
            
            context_flow.append(ContextFlowEntry(
                timestamp=datetime.utcnow().isoformat(),
                phase="verify",
                source="execution",
                target="validation",
                influence_type="pattern",
                weight=validation.confidence if validation else 0.0,
                note=f"Validation: {validation.confidence:.2f} confidence" if validation else "No validation"
            ))
            
            # Ensure blueprint carries minimal flow + incompleteness for receipts/UI
            if not blueprint.context_flow:
                blueprint.context_flow.append(
                    ContextFlowEntry(
                        timestamp=datetime.utcnow().isoformat(),
                        phase="orient",
                        source="spec_generator",
                        target="blueprint",
                        influence_type="heuristic",
                        weight=0.5,
                        note="Auto-seeded context flow"
                    )
                )
            if not blueprint.incompleteness:
                blueprint.incompleteness = IncompletenessAssessment(
                    score=0.5,
                    missing_elements=["Validation pending"],
                    next_steps=["Run executor and validation"],
                    auto_approve_allowed=False,
                )

            # Check if successful
            if validation and validation.valid:
                break
            
            # Failed - try error hook for correction
            if self.on_error and iteration < self.max_retries:
                error_msg = "; ".join(c.details for c in validation.checks if not c.passed) if validation else "Unknown error"
                correction = self.on_error(error_msg)
                if correction:
                    # Could re-generate blueprint with correction hint
                    # For now, just retry
                    continue
            
            break
        
        # ===================
        # CONSTITUTIONAL POST-CHECK
        # ===================
        # Build a temporary result to check post-conditions
        temp_result = BuildResult(
            mode="build",
            success=validation.valid if validation else False,
            context_flow=context_flow,
            world_impact=WorldImpactAssessment(
                category=council_synthesis.world_impact_category if council_synthesis else None
            )
        )
        
        post_enforcement = self.enforcer.check_post_conditions(
            result=temp_result,
            context={
                "blueprint": blueprint,
                "validation": validation,
                "file_results": file_results,
                "mode": "build"
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
        post_enforcement_warnings = []
        if not post_enforcement.allowed:
            violation_receipt = ConstitutionalViolationReceipt(
                invariant_id=post_enforcement.blocking_invariant.invariant_id if post_enforcement.blocking_invariant else "",
                invariant_name=post_enforcement.blocking_invariant.name if post_enforcement.blocking_invariant else "",
                severity=post_enforcement.blocking_invariant.severity if post_enforcement.blocking_invariant else None,
                violation_description=post_enforcement.blocking_reason,
                escalated_to_guardian=True  # Auto-escalate violations
            )
            self._enforcement_receipts.append(violation_receipt)
            post_enforcement_warnings = post_enforcement.warnings
        else:
            # Log pass receipt
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
        
        # Lightweight validation gate: require flow + incompleteness metadata
        gate_errors = []
        
        # Add any post-enforcement warnings as errors
        for warning in post_enforcement_warnings:
            gate_errors.append(
                ModeError(
                    code=ErrorCode.VERIFICATION_FAILED,
                    stage="verify",
                    message=warning,
                    recoverable=False,
                    organism_action="warn"
                )
            )
        if not blueprint.context_flow:
            gate_errors.append(
                ModeError(
                    code=ErrorCode.LOW_CONFIDENCE,
                    stage="verify",
                    message="context_flow missing; cannot assert traceability",
                    recoverable=True,
                    suggested_action="Ensure spec_generator seeds flow entries"
                )
            )
        if not blueprint.incompleteness:
            gate_errors.append(
                ModeError(
                    code=ErrorCode.INCOMPLETE_BUT_SAFE,
                    stage="verify",
                    message="incompleteness assessment missing; auto-approve not allowed",
                    recoverable=True,
                    suggested_action="Attach incompleteness assessment before approval"
                )
            )

        # Build cognition summary
        cognition = CognitionSummary(
            observed=f"Build request: {intent.category.value}",
            oriented=f"Generated blueprint with {len(blueprint.files)} files",
            acted=f"Executed in {iteration} iteration(s), confidence: {validation.confidence:.2f}" if validation else "Execution incomplete",
            key_decision=f"Category: {intent.category.value}",
            confidence_rationale=self._confidence_rationale(validation) if validation else "No validation"
        )
        
        # Build incompleteness assessment
        incompleteness = self._assess_incompleteness(file_results, validation)
        
        # Build world impact assessment
        world_impact = WorldImpactAssessment(
            category=None,
            impact_score=0.1,
            verification_tier="standard"
        )
        
        # Build color tiles
        color_tiles = self._build_color_tiles(intent, file_results, validation)
        
        # Build conversation response
        conversation_response = self._build_response(file_results, validation, blueprint)
        
        return BuildResult(
            result_id=str(uuid.uuid4()),
            spec_version=SPEC_VERSION,
            mode="build",
            success=(validation.valid if validation else False) and not gate_errors,
            errors=gate_errors,
            context_flow=context_flow,
            color_tiles=color_tiles,
            cognition_summary=cognition,
            incompleteness=incompleteness,
            world_impact=world_impact,
            total_time_ms=elapsed_ms,
            intent=intent,
            blueprint=blueprint,
            file_results=file_results,
            command_results=command_results,
            validation=validation,
            rollback_available=self.executor.enable_rollback,
            rollback_data=self.executor.get_rollback_data(),
            conversation_response=conversation_response
        )

    def process_with_synthesis(
        self,
        intent_envelope: IntentEnvelope,
        council_synthesis: QuintetSynthesis,
        query: str,
        synthesis: Optional[Dict[str, Any]] = None,
    ) -> BuildResult:
        """
        Convenience wrapper that threads the council synthesis/intent through.
        """
        return self.process(
            query=query,
            synthesis=synthesis,
            intent_envelope=intent_envelope,
            council_synthesis=council_synthesis,
        )
    
    def _not_build_result(
        self,
        query: str,
        intent: BuildIntent,
        start_time: float
    ) -> BuildResult:
        """Return result for non-build query."""
        elapsed = (time.time() - start_time) * 1000
        
        return BuildResult(
            success=False,
            mode="build",
            errors=[ModeError(
                code=ErrorCode.INTENT_UNCLEAR,
                stage="detect",
                message="Query does not appear to be a build request",
                recoverable=True,
                suggested_action="Try Math Mode instead"
            )],
            total_time_ms=elapsed,
            intent=intent,
            conversation_response="This doesn't appear to be a build request. Can you clarify what you'd like to build?"
        )
    
    def _approval_denied_result(
        self,
        query: str,
        intent: BuildIntent,
        blueprint: ProjectBlueprint,
        start_time: float,
        context_flow
    ) -> BuildResult:
        """Return result when approval is denied."""
        elapsed = (time.time() - start_time) * 1000
        
        return BuildResult(
            success=False,
            mode="build",
            errors=[ModeError(
                code=ErrorCode.PLAN_ERROR,
                stage="decide",
                message="Blueprint was not approved",
                recoverable=True,
                suggested_action="Review and modify the blueprint"
            )],
            context_flow=context_flow,
            total_time_ms=elapsed,
            intent=intent,
            blueprint=blueprint,
            conversation_response="Build blueprint was not approved. Would you like to modify it?"
        )
    
    def _constitutional_block_result(
        self,
        query: str,
        intent: BuildIntent,
        blueprint: ProjectBlueprint,
        start_time: float,
        context_flow,
        enforcement: EnforcementResult
    ) -> BuildResult:
        """Return result when constitutional pre-check blocks execution."""
        elapsed = (time.time() - start_time) * 1000
        
        blocking_inv = enforcement.blocking_invariant
        inv_name = blocking_inv.name if blocking_inv else "Unknown"
        
        return BuildResult(
            success=False,
            mode="build",
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
            blueprint=blueprint,
            conversation_response=f"⚠️ **Constitutional Block**: This action was blocked by the `{inv_name}` invariant.\n\n**Reason:** {enforcement.blocking_reason}\n\nPlease ensure compliance before retrying."
        )
    
    def _confidence_rationale(self, validation) -> str:
        """Build rationale for confidence level."""
        if validation.confidence >= 0.9:
            return "High confidence: all validations passed"
        elif validation.confidence >= 0.7:
            return "Good confidence: most validations passed"
        elif validation.confidence >= 0.5:
            return "Moderate confidence: some checks passed"
        else:
            return "Low confidence: validation issues detected"
    
    def _assess_incompleteness(self, file_results, validation) -> IncompletenessAssessment:
        """Assess build completeness."""
        if not file_results:
            return IncompletenessAssessment(
                score=0.0,
                missing_elements=["No files created"],
                next_steps=["Review blueprint and retry"]
            )
        
        successful = sum(1 for fr in file_results if fr.success)
        total = len(file_results)
        score = successful / total if total > 0 else 0.0
        
        missing = [fr.path for fr in file_results if not fr.success]
        
        return IncompletenessAssessment(
            score=score,
            missing_elements=missing,
            partial_elements=[],
            next_steps=["Fix failed files"] if missing else []
        )
    
    def _build_color_tiles(self, intent, file_results, validation) -> ColorTileGrid:
        """Build 3x3 color tile grid."""
        tiles = []
        
        # Row A: Observation
        tiles.append(ColorTile(
            tile_id="A1",
            color="#4CAF50" if intent.is_build else "#F44336",
            mood="confident" if intent.confidence > 0.7 else "uncertain",
            signal="success" if intent.is_build else "warning",
            tagline="Build" if intent.is_build else "Not Build",
            value=intent.confidence
        ))
        tiles.append(ColorTile(
            tile_id="A2",
            color=self._category_color(intent.category),
            mood="confident",
            signal="success",
            tagline=intent.category.value[:10].replace("_", " ").title()
        ))
        tiles.append(ColorTile(
            tile_id="A3",
            color="#2196F3",
            mood="confident",
            signal="success",
            tagline=f"{len(intent.technologies)} Tech" if intent.technologies else "Generic"
        ))
        
        # Row B: Orientation/Action
        files_ok = sum(1 for fr in file_results if fr.success) if file_results else 0
        files_total = len(file_results) if file_results else 0
        
        tiles.append(ColorTile(
            tile_id="B1",
            color="#4CAF50" if files_ok == files_total else "#FF9800",
            mood="satisfied" if files_ok == files_total else "uncertain",
            signal="success" if files_ok == files_total else "warning",
            tagline=f"{files_ok}/{files_total} Files"
        ))
        
        tiles.append(ColorTile(
            tile_id="B2",
            color="#9C27B0",
            mood="confident",
            signal="success",
            tagline="Executed"
        ))
        
        # Validation tile
        if validation:
            val_color = "#4CAF50" if validation.valid else "#F44336"
            tiles.append(ColorTile(
                tile_id="B3",
                color=val_color,
                mood="satisfied" if validation.valid else "alert",
                signal="success" if validation.valid else "error",
                tagline=f"{validation.confidence:.0%} Valid",
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
            color="#607D8B",
            mood="confident",
            signal="success",
            tagline="Build Mode"
        ))
        tiles.append(ColorTile(
            tile_id="C2",
            color="#00BCD4",
            mood="confident",
            signal="success",
            tagline="Tier 0"
        ))
        tiles.append(ColorTile(
            tile_id="C3",
            color="#8BC34A" if (validation and validation.valid) else "#FF5722",
            mood="satisfied" if (validation and validation.valid) else "alert",
            signal="success" if (validation and validation.valid) else "warning",
            tagline="Complete" if (validation and validation.valid) else "Issues"
        ))
        
        return ColorTileGrid(
            grid_id=str(uuid.uuid4()),
            mode="build",
            tiles=tiles
        )
    
    def _category_color(self, category: BuildCategory) -> str:
        """Get color for build category."""
        colors = {
            BuildCategory.CREATE_FILE: "#4CAF50",
            BuildCategory.CREATE_MODULE: "#8BC34A",
            BuildCategory.CREATE_PROJECT: "#009688",
            BuildCategory.MODIFY_FILE: "#03A9F4",
            BuildCategory.REFACTOR: "#673AB7",
            BuildCategory.ADD_FEATURE: "#FF9800",
            BuildCategory.FIX_BUG: "#F44336",
            BuildCategory.ADD_TESTS: "#9C27B0",
            BuildCategory.CONFIGURE: "#607D8B",
            BuildCategory.DEPLOY: "#795548",
        }
        return colors.get(category, "#757575")
    
    def _build_response(self, file_results, validation, blueprint) -> str:
        """Build human-friendly response."""
        if not file_results:
            return "No files were created or modified."
        
        response = []
        
        # Summary
        successful = sum(1 for fr in file_results if fr.success)
        response.append(f"**Build Complete:** {successful}/{len(file_results)} files created/modified")
        
        # List files
        response.append("\n**Files:**")
        for fr in file_results:
            status = "✓" if fr.success else "✗"
            response.append(f"- {status} `{fr.path}`")
        
        # Validation
        if validation:
            response.append(f"\n**Validation:** {'Passed' if validation.valid else 'Issues detected'} ({validation.confidence:.0%} confidence)")
        
        return "\n".join(response)


# Convenience function
def create_build_mode(
    project_root: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> UltraModeOrchestrator:
    """Create and return a configured UltraModeOrchestrator."""
    return UltraModeOrchestrator(project_root, config)

