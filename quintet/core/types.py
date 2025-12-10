"""
Quintet Core Types - SINGLE SOURCE OF TRUTH
============================================

Spec Version: quintet-ultra-math-v1.1

This module defines ALL shared types used by both Build Mode and Math Mode.
Neither mode should redefine these types - only import and use them.

Implementation Tiers:
- Tier 0 (Required): Build Mode + these core types
- Tier 1 (Required for Math): Math Mode core with SymPy + NumPy
- Tier 2 (Optional): Advanced packs (CVXPY, statsmodels, PDE, Lean, etc.)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Protocol
from datetime import datetime
from enum import Enum
import uuid


# =============================================================================
# SPEC VERSION
# =============================================================================

SPEC_VERSION = "quintet-ultra-math-v1.1"


# =============================================================================
# ERROR TAXONOMY
# =============================================================================

class ErrorCode(Enum):
    """Canonical error codes for all modes."""
    
    # Detection/Parsing
    PARSE_ERROR = "PARSE_ERROR"
    INTENT_UNCLEAR = "INTENT_UNCLEAR"
    
    # Planning
    PLAN_ERROR = "PLAN_ERROR"
    NO_VIABLE_PLAN = "NO_VIABLE_PLAN"
    CONTRADICTION_UNRESOLVED = "CONTRADICTION_UNRESOLVED"
    
    # Execution
    EXECUTION_ERROR = "EXECUTION_ERROR"
    TIMEOUT = "TIMEOUT"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"
    
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    
    # Safety
    INCOMPLETE_BUT_SAFE = "INCOMPLETE_BUT_SAFE"
    HIGH_IMPACT_LOW_CONFIDENCE = "HIGH_IMPACT_LOW_CONFIDENCE"
    WORLD_IMPACT_BLOCKED = "WORLD_IMPACT_BLOCKED"


@dataclass
class ModeError:
    """Structured error for any mode."""
    code: ErrorCode
    stage: str              # "detect" | "parse" | "plan" | "execute" | "validate" | "explain"
    message: str
    recoverable: bool
    details: Optional[Dict[str, Any]] = None
    suggested_action: Optional[str] = None
    organism_action: str = "log"  # "log" | "warn" | "block"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code.value,
            "stage": self.stage,
            "message": self.message,
            "recoverable": self.recoverable,
            "details": self.details,
            "suggested_action": self.suggested_action,
            "organism_action": self.organism_action
        }


# =============================================================================
# VALIDATION (Shared by Build and Math)
# =============================================================================

class MethodCategory(str, Enum):
    """Categories of verification methods for diversity scoring."""
    SYMBOLIC = "symbolic"       # substitution, symbolic_simplify, formal_proof, syntax
    NUMERIC = "numeric"         # numerical spot checks, monte carlo
    STRUCTURAL = "structural"   # bounds, sanity, dimensional_analysis, imports
    ALTERNATIVE = "alternative" # alternative methods, cross-backend verification


@dataclass
class ValidationCheck:
    """Single validation check result."""
    check_name: str                   # "substitution", "syntax", "imports", etc.
    check_type: str                   # "core" | "domain" | "formal" | "build"
    passed: bool
    confidence_contribution: float    # How much this adds to confidence (0.0-1.0)
    details: str
    execution_time_ms: float = 0.0
    method_used: Optional[str] = None
    method_category: Optional[str] = None  # "symbolic" | "numeric" | "structural" | "alternative"
    data: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Complete validation result - SHARED by Build and Math."""
    valid: bool
    confidence: float                 # 0.0 to 1.0
    checks: List[ValidationCheck] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[ModeError] = field(default_factory=list)
    suggested_review: bool = False
    domain: Optional[str] = None      # "build" | "pure_math" | "stats" | etc.
    
    @property
    def checks_passed(self) -> int:
        """Computed property - number of passed checks."""
        return sum(1 for c in self.checks if c.passed)
    
    @property
    def checks_failed(self) -> int:
        """Computed property - number of failed checks."""
        return sum(1 for c in self.checks if not c.passed)
    
    @property
    def diversity_score(self) -> float:
        """
        How diverse were the verification methods?
        High diversity = stronger trust.
        
        Uses method_category field if present, falls back to check_name matching.
        """
        method_name_mapping = {
            "substitution": MethodCategory.SYMBOLIC.value,
            "symbolic_simplify": MethodCategory.SYMBOLIC.value,
            "formal_proof": MethodCategory.SYMBOLIC.value,
            "syntax": MethodCategory.SYMBOLIC.value,
            "gradient_verification": MethodCategory.SYMBOLIC.value,
            "numerical": MethodCategory.NUMERIC.value,
            "numerical_spot_check": MethodCategory.NUMERIC.value,
            "monte_carlo": MethodCategory.NUMERIC.value,
            "bounds": MethodCategory.STRUCTURAL.value,
            "sanity": MethodCategory.STRUCTURAL.value,
            "type_check": MethodCategory.STRUCTURAL.value,
            "dimensional_analysis": MethodCategory.STRUCTURAL.value,
            "imports": MethodCategory.STRUCTURAL.value,
            "alternative_method": MethodCategory.ALTERNATIVE.value,
            "cross_backend": MethodCategory.ALTERNATIVE.value,
            "test_execution": MethodCategory.ALTERNATIVE.value,
        }
        
        categories_used = set()
        for check in self.checks:
            if check.passed:
                # Prefer explicit method_category if set
                if check.method_category:
                    categories_used.add(check.method_category)
                # Fall back to check_name mapping
                elif check.check_name in method_name_mapping:
                    categories_used.add(method_name_mapping[check.check_name])
        
        all_categories = {c.value for c in MethodCategory}
        return len(categories_used) / len(all_categories) if all_categories else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "confidence": self.confidence,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "diversity_score": self.diversity_score,
            "checks": [
                {
                    "check_name": c.check_name,
                    "check_type": c.check_type,
                    "passed": c.passed,
                    "confidence_contribution": c.confidence_contribution,
                    "details": c.details,
                    "method_category": c.method_category
                }
                for c in self.checks
            ],
            "warnings": self.warnings,
            "errors": [e.to_dict() for e in self.errors],  # FIX: include errors
            "suggested_review": self.suggested_review,
            "domain": self.domain
        }


# =============================================================================
# CONTEXT FLOW
# =============================================================================

@dataclass
class ContextFlowEntry:
    """Single entry in context flow log."""
    timestamp: str              # ISO 8601
    phase: str                  # "observe" | "orient" | "architect" | "decide" | "act" | "verify"
    source: str                 # What influenced this (file, component, check)
    target: str                 # What was affected
    influence_type: str         # "dependency" | "pattern" | "constraint" | "heuristic" | "retrieval"
    weight: float               # 0.0-1.0
    note: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "phase": self.phase,
            "source": self.source,
            "target": self.target,
            "influence_type": self.influence_type,
            "weight": self.weight,
            "note": self.note
        }


# =============================================================================
# COGNITION SUMMARY
# =============================================================================

@dataclass
class CognitionSummary:
    """3-sentence cognition summary."""
    observed: str               # What was detected/understood
    oriented: str               # How context shaped the approach
    acted: str                  # What changed as a result
    key_decision: str           # Single most important choice
    confidence_rationale: str   # Why confidence is at this level
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "observed": self.observed,
            "oriented": self.oriented,
            "acted": self.acted,
            "key_decision": self.key_decision,
            "confidence_rationale": self.confidence_rationale
        }


# =============================================================================
# INCOMPLETENESS
# =============================================================================

@dataclass
class IncompletenessAssessment:
    """Assessment of solution completeness."""
    score: float                # 0.0 (fully incomplete) to 1.0 (fully complete)
    missing_elements: List[str] = field(default_factory=list)
    partial_elements: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    auto_approve_allowed: bool = True
    
    def __post_init__(self):
        """Enforce gating rules."""
        if self.score < 0.7:
            self.auto_approve_allowed = False
        if self.score < 0.5 and not self.next_steps:
            # Don't raise - just ensure next_steps is populated
            self.next_steps = ["Manual review required due to low completeness"]
    
    @property
    def is_acceptable(self) -> bool:
        return self.score >= 0.7
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "missing_elements": self.missing_elements,
            "partial_elements": self.partial_elements,
            "next_steps": self.next_steps,
            "auto_approve_allowed": self.auto_approve_allowed,
            "is_acceptable": self.is_acceptable
        }


# =============================================================================
# WORLD IMPACT
# =============================================================================

@dataclass
class WorldImpactAssessment:
    """Assessment of real-world impact and safeguards."""
    category: Optional[str] = None  # "healthcare_medicine" | "climate_environment" | etc.
    impact_score: float = 0.0       # 0.0-1.0
    verification_tier: str = "standard"  # "standard" | "elevated" | "critical"
    confidence_adjustment: float = 0.0   # Negative adjustment to confidence
    required_checks: List[str] = field(default_factory=list)
    disclaimer: Optional[str] = None
    logged_to_receipt: bool = False
    
    def __post_init__(self):
        """
        Enforce tier escalation rules based on impact score and category.
        
        Rules:
        - impact_score >= 0.8 → critical (regardless of category)
        - impact_score >= 0.3 AND category present → elevated
        - Otherwise → keep current tier (default: standard)
        """
        if self.impact_score >= 0.8:
            self.verification_tier = "critical"
        elif self.category and self.impact_score >= 0.3 and self.verification_tier == "standard":
            self.verification_tier = "elevated"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "impact_score": self.impact_score,
            "verification_tier": self.verification_tier,
            "confidence_adjustment": self.confidence_adjustment,
            "required_checks": self.required_checks,
            "disclaimer": self.disclaimer,
            "logged_to_receipt": self.logged_to_receipt
        }


# =============================================================================
# COLOR TILES
# =============================================================================

@dataclass
class ColorTile:
    """Single color tile in the 3x3 grid."""
    tile_id: str                # "A1", "B2", "C3", etc.
    color: str                  # Hex color code
    mood: str                   # "confident" | "uncertain" | "alert" | "satisfied"
    signal: str                 # "success" | "warning" | "error" | "waiting"
    tagline: str                # Two-word summary
    value: Optional[float] = None           # 0.0-1.0 for gradient tiles
    data_reference: str = ""                # Path to source data
    data_snapshot: Optional[Any] = None     # Actual value
    memory_embedding_id: Optional[str] = None
    related_tiles: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tile_id": self.tile_id,
            "color": self.color,
            "mood": self.mood,
            "signal": self.signal,
            "tagline": self.tagline,
            "value": self.value,
            "data_reference": self.data_reference,
            "memory_embedding_id": self.memory_embedding_id
        }


@dataclass
class ColorTileGrid:
    """Complete 3x3 tile grid."""
    grid_id: str
    mode: str                   # "build" | "math"
    spec_version: str = SPEC_VERSION
    tiles: List[ColorTile] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    problem_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "grid_id": self.grid_id,
            "mode": self.mode,
            "spec_version": self.spec_version,
            "tiles": [t.to_dict() for t in self.tiles],
            "generated_at": self.generated_at,
            "problem_hash": self.problem_hash
        }
    
    def to_human_readable(self) -> str:
        """ASCII art representation."""
        lines = [f"╔═══════════════════════════════════╗"]
        lines.append(f"║  Color Tiles ({self.mode:5}) {self.spec_version}  ║")
        lines.append(f"╠═══════════╦═══════════╦═══════════╣")
        for row in ["A", "B", "C"]:
            row_tiles = [t for t in self.tiles if t.tile_id.startswith(row)]
            row_str = "║"
            for col in ["1", "2", "3"]:
                tile = next((t for t in row_tiles if t.tile_id == f"{row}{col}"), None)
                if tile:
                    row_str += f" {tile.tagline[:9]:^9} ║"
                else:
                    row_str += f" {'---':^9} ║"
            lines.append(row_str)
            if row != "C":
                lines.append(f"╠═══════════╬═══════════╬═══════════╣")
        lines.append(f"╚═══════════╩═══════════╩═══════════╝")
        return "\n".join(lines)


# =============================================================================
# MODE RESULT BASE
# =============================================================================

@dataclass
class ModeResultBase:
    """
    Base result class - inherited/composed by BuildResult and MathModeResult.
    
    Both Build Mode and Math Mode results should include these fields.
    Mode-specific results add their own fields on top.
    """
    # Identity
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    spec_version: str = SPEC_VERSION
    mode: str = "unknown"
    
    # Core status
    success: bool = False
    errors: List[ModeError] = field(default_factory=list)
    
    # Shared metadata (stable contracts)
    context_flow: List[ContextFlowEntry] = field(default_factory=list)
    color_tiles: Optional[ColorTileGrid] = None
    cognition_summary: Optional[CognitionSummary] = None
    incompleteness: Optional[IncompletenessAssessment] = None
    world_impact: Optional[WorldImpactAssessment] = None
    
    # Timing
    total_time_ms: float = 0.0
    
    def to_base_dict(self) -> Dict[str, Any]:
        """Serialize base fields - call this from subclass to_dict()."""
        return {
            "result_id": self.result_id,
            "spec_version": self.spec_version,
            "mode": self.mode,
            "success": self.success,
            "errors": [e.to_dict() for e in self.errors],
            "context_flow": [cf.to_dict() for cf in self.context_flow],
            "color_tiles": self.color_tiles.to_dict() if self.color_tiles else None,
            "cognition_summary": self.cognition_summary.to_dict() if self.cognition_summary else None,
            "incompleteness": self.incompleteness.to_dict() if self.incompleteness else None,
            "world_impact": self.world_impact.to_dict() if self.world_impact else None,
            "total_time_ms": self.total_time_ms
        }


# =============================================================================
# MODE PROTOCOL
# =============================================================================

class Mode(Protocol):
    """Protocol that both BuildMode and MathMode must implement."""
    
    @property
    def mode_name(self) -> str:
        """Return mode identifier: 'build' or 'math'."""
        ...
    
    def detect(self, query: str, synthesis: Optional[Dict[str, Any]] = None) -> Any:
        """Detect if this mode should handle the query. Returns mode-specific Intent."""
        ...
    
    def process(self, query: str, synthesis: Optional[Dict[str, Any]] = None) -> ModeResultBase:
        """Process the query. Returns result extending ModeResultBase."""
        ...


# =============================================================================
# RESOURCE LIMITS
# =============================================================================

@dataclass
class ResourceLimits:
    """Resource limits per compute tier."""
    max_wall_time_ms: int
    max_plans: int
    max_solutions_per_plan: int
    max_verification_paths: int
    max_memory_mb: int
    max_shell_runtime_ms: int


RESOURCE_LIMITS = {
    "light": ResourceLimits(
        max_wall_time_ms=5000,
        max_plans=1,
        max_solutions_per_plan=1,
        max_verification_paths=2,
        max_memory_mb=256,
        max_shell_runtime_ms=10000
    ),
    "standard": ResourceLimits(
        max_wall_time_ms=30000,
        max_plans=3,
        max_solutions_per_plan=2,
        max_verification_paths=4,
        max_memory_mb=1024,
        max_shell_runtime_ms=60000
    ),
    "deep_search": ResourceLimits(
        max_wall_time_ms=300000,
        max_plans=10,
        max_solutions_per_plan=5,
        max_verification_paths=8,
        max_memory_mb=4096,
        max_shell_runtime_ms=300000
    )
}


# =============================================================================
# RECEIPTS (for organism/Guardian integration)
# =============================================================================

@dataclass
class Receipt:
    """
    Base receipt for organism relay.
    
    Every receipt gets a unique ID and optional correlation_id for linking
    multiple receipts from one episode (useful for Causal Decision Lab).
    """
    receipt_type: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    mode: str = "unknown"
    result_id: Optional[str] = None
    receipt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None  # Link multiple receipts from one episode
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "receipt_type": self.receipt_type,
            "timestamp": self.timestamp,
            "mode": self.mode,
            "result_id": self.result_id,
            "receipt_id": self.receipt_id,
            "correlation_id": self.correlation_id
        }


# =============================================================================
# EPISODE (Causal Decision Lab foundation)
# =============================================================================

@dataclass
class Episode:
    """
    A single decision episode through the organism.
    
    This is the canonical unit for logging, training, and causal analysis.
    Each episode captures one query → processing → result cycle.
    """
    episode_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""                         # raw user/system query
    mode: str = "unknown"                   # "build" | "math" | "causal" | ...
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    finished_at: Optional[str] = None

    result: Optional[ModeResultBase] = None
    validation: Optional[ValidationResult] = None
    world_impact: Optional[WorldImpactAssessment] = None
    incompleteness: Optional[IncompletenessAssessment] = None

    receipts: List[Receipt] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)  # extra tags: tenant, domain, etc.

    @property
    def duration_ms(self) -> Optional[float]:
        if not self.finished_at:
            return None
        try:
            start = datetime.fromisoformat(self.started_at.replace('Z', '+00:00'))
            end = datetime.fromisoformat(self.finished_at.replace('Z', '+00:00'))
            return (end - start).total_seconds() * 1000.0
        except:
            return None
    
    @property
    def trust_score(self) -> float:
        """Compute scalar trust score from validation, incompleteness, and world_impact."""
        return compute_trust_score(self.validation, self.incompleteness, self.world_impact)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "query": self.query,
            "mode": self.mode,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "trust_score": self.trust_score,
            "result": self.result.to_base_dict() if self.result else None,
            "validation": self.validation.to_dict() if self.validation else None,
            "world_impact": self.world_impact.to_dict() if self.world_impact else None,
            "incompleteness": self.incompleteness.to_dict() if self.incompleteness else None,
            "receipts": [r.to_dict() for r in self.receipts],
            "metadata": self.metadata,
        }


# =============================================================================
# TRUST SCORE (mode-neutral scalar for Guardian / tiles)
# =============================================================================

def compute_trust_score(
    validation: Optional[ValidationResult],
    incompleteness: Optional[IncompletenessAssessment],
    world_impact: Optional[WorldImpactAssessment],
) -> float:
    """
    Compute a scalar trust score (0.0-1.0) from existing signals.
    
    This is deliberately simple and explicit so we can evolve it.
    Used by:
    - Guardian gating
    - Color tiles
    - Causal Decision Lab decision boundaries
    """
    if not validation:
        return 0.0

    base_conf = validation.confidence               # primary signal
    diversity = validation.diversity_score or 0.0   # verification diversity
    complete = incompleteness.score if incompleteness else 0.5  # default to 0.5 if unknown
    adj = world_impact.confidence_adjustment if world_impact else 0.0

    # Simple weighted blend (tune these later or learn from data):
    score = (
        0.6 * base_conf +
        0.2 * diversity +
        0.2 * complete +
        adj
    )

    return max(0.0, min(1.0, score))


# =============================================================================
# STRESS / SURVIVAL CONTRACTS
# =============================================================================

class StressLevel(Enum):
    """System stress levels for adaptive behavior."""
    NOMINAL = "nominal"         # Normal operation
    ELEVATED = "elevated"       # Some resource pressure
    HIGH = "high"               # Significant pressure, consider degradation
    CRITICAL = "critical"       # Near limits, aggressive degradation


@dataclass
class StressProfile:
    """
    Current system stress profile.

    Used by router and modes to adapt behavior under resource pressure.
    """
    level: StressLevel = StressLevel.NOMINAL

    # Resource utilization (0.0-1.0)
    token_utilization: float = 0.0          # current / max tokens
    call_utilization: float = 0.0           # current / max calls
    cost_utilization: float = 0.0           # current / max cost (if tracked)
    latency_pressure: float = 0.0           # avg latency / target latency

    # Computed thresholds
    degradation_recommended: bool = False   # Should we skip optional features?
    shadow_mode_recommended: bool = False   # Should we run in shadow mode?

    # Time-based stress
    time_remaining_ms: Optional[float] = None   # Wall-clock budget remaining
    calls_remaining: int = 0
    tokens_remaining: int = 0

    def __post_init__(self):
        """Compute derived flags from utilization."""
        max_util = max(self.token_utilization, self.call_utilization, self.cost_utilization)

        if max_util >= 0.95 or self.level == StressLevel.CRITICAL:
            self.degradation_recommended = True
            self.shadow_mode_recommended = True
        elif max_util >= 0.8 or self.level == StressLevel.HIGH:
            self.degradation_recommended = True
        elif max_util >= 0.6 or self.level == StressLevel.ELEVATED:
            pass  # Watch but don't degrade yet

    @classmethod
    def from_trace_stats(cls, stats: Dict[str, Any], config_limits: Optional[Dict[str, Any]] = None) -> "StressProfile":
        """Build stress profile from router trace stats."""
        total_calls = stats.get("total_calls", 0)
        total_tokens = stats.get("total_tokens", 0)
        call_limit = stats.get("call_limit", 50)
        token_limit = stats.get("token_limit", 100000)

        call_util = total_calls / call_limit if call_limit > 0 else 0.0
        token_util = total_tokens / token_limit if token_limit > 0 else 0.0

        max_util = max(call_util, token_util)
        if max_util >= 0.95:
            level = StressLevel.CRITICAL
        elif max_util >= 0.8:
            level = StressLevel.HIGH
        elif max_util >= 0.6:
            level = StressLevel.ELEVATED
        else:
            level = StressLevel.NOMINAL

        return cls(
            level=level,
            token_utilization=token_util,
            call_utilization=call_util,
            calls_remaining=stats.get("calls_remaining", call_limit - total_calls),
            tokens_remaining=stats.get("tokens_remaining", token_limit - total_tokens),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "token_utilization": self.token_utilization,
            "call_utilization": self.call_utilization,
            "cost_utilization": self.cost_utilization,
            "latency_pressure": self.latency_pressure,
            "degradation_recommended": self.degradation_recommended,
            "shadow_mode_recommended": self.shadow_mode_recommended,
            "time_remaining_ms": self.time_remaining_ms,
            "calls_remaining": self.calls_remaining,
            "tokens_remaining": self.tokens_remaining,
        }


class SurvivalOutcome(Enum):
    """Outcome of a survival check."""
    SURVIVED = "survived"               # Completed within budget
    DEGRADED = "degraded"               # Completed with reduced features
    PARTIAL = "partial"                 # Partially completed
    FAILED = "failed"                   # Could not complete
    TIMEOUT = "timeout"                 # Timed out
    BUDGET_EXHAUSTED = "budget_exhausted"  # Ran out of tokens/calls


@dataclass
class SurvivalReceipt(Receipt):
    """
    Receipt documenting how a component survived resource pressure.

    Useful for:
    - Post-hoc analysis of degradation decisions
    - Training Causal Decision Lab on resource management
    - Auditing why certain features were skipped
    """
    receipt_type: str = "survival"

    # Stress context at time of decision
    stress_profile: Optional[StressProfile] = None
    outcome: SurvivalOutcome = SurvivalOutcome.SURVIVED

    # What was affected
    component: str = ""                 # "debate_loop", "llm_explainer", etc.
    action_taken: str = ""              # "skipped", "degraded", "ran_normally"

    # Resource usage
    tokens_used: int = 0
    calls_used: int = 0
    time_used_ms: float = 0.0

    # Degradation details
    features_skipped: List[str] = field(default_factory=list)
    fallback_used: bool = False
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "stress_profile": self.stress_profile.to_dict() if self.stress_profile else None,
            "outcome": self.outcome.value,
            "component": self.component,
            "action_taken": self.action_taken,
            "tokens_used": self.tokens_used,
            "calls_used": self.calls_used,
            "time_used_ms": self.time_used_ms,
            "features_skipped": self.features_skipped,
            "fallback_used": self.fallback_used,
            "error_message": self.error_message,
        })
        return base


@dataclass
class PromotionPolicy:
    """
    Policy for promoting components from shadow mode to production.

    Shadow mode: Component runs but results are logged, not used.
    Production: Component results are used in the pipeline.
    """
    component: str                      # "debate_loop", "llm_validator", etc.
    mode: str = "shadow"                # "shadow" | "production" | "disabled"

    # Promotion criteria
    min_successful_runs: int = 10       # Must succeed N times in shadow
    max_failure_rate: float = 0.1       # Max 10% failures to promote
    min_confidence_avg: float = 0.7     # Average confidence must be >= 0.7

    # Tracking
    shadow_runs: int = 0
    shadow_successes: int = 0
    shadow_failures: int = 0
    confidence_sum: float = 0.0

    # High-risk domain restrictions
    high_risk_domains: List[str] = field(default_factory=lambda: [
        "chemistry", "biology", "weapons", "malware", "financial", "medical"
    ])
    shadow_only_for_high_risk: bool = True  # Force shadow mode for high-risk

    def record_run(self, success: bool, confidence: float = 0.0) -> None:
        """Record a shadow run result."""
        self.shadow_runs += 1
        if success:
            self.shadow_successes += 1
        else:
            self.shadow_failures += 1
        self.confidence_sum += confidence

    @property
    def failure_rate(self) -> float:
        if self.shadow_runs == 0:
            return 0.0
        return self.shadow_failures / self.shadow_runs

    @property
    def avg_confidence(self) -> float:
        if self.shadow_runs == 0:
            return 0.0
        return self.confidence_sum / self.shadow_runs

    @property
    def ready_for_promotion(self) -> bool:
        """Check if component meets promotion criteria."""
        if self.mode != "shadow":
            return False
        if self.shadow_runs < self.min_successful_runs:
            return False
        if self.failure_rate > self.max_failure_rate:
            return False
        if self.avg_confidence < self.min_confidence_avg:
            return False
        return True

    def should_use_shadow(self, domain: Optional[str] = None) -> bool:
        """Check if shadow mode should be used for this domain."""
        if self.mode == "disabled":
            return False
        if self.mode == "shadow":
            return True
        # Production mode but high-risk domain
        if self.shadow_only_for_high_risk and domain:
            if domain.lower() in self.high_risk_domains:
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "mode": self.mode,
            "min_successful_runs": self.min_successful_runs,
            "max_failure_rate": self.max_failure_rate,
            "min_confidence_avg": self.min_confidence_avg,
            "shadow_runs": self.shadow_runs,
            "shadow_successes": self.shadow_successes,
            "shadow_failures": self.shadow_failures,
            "failure_rate": self.failure_rate,
            "avg_confidence": self.avg_confidence,
            "ready_for_promotion": self.ready_for_promotion,
            "shadow_only_for_high_risk": self.shadow_only_for_high_risk,
        }


# =============================================================================
# EPISODE LOGGING (JSONL sink for Causal Lab dataset)
# =============================================================================

def append_episode(path: str, episode: Episode) -> None:
    """
    Append one episode as JSONL. Safe to call from any mode.
    
    Creates parent directories if needed.
    This is the primary dataset sink for Causal Decision Lab.
    """
    import json
    from pathlib import Path
    
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(episode.to_dict(), ensure_ascii=False, default=str) + "\n")

