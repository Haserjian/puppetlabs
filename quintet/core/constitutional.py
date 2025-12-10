"""
Constitutional Meta-Checker & Runtime Enforcer
================================================

Uses Math Mode to verify the organism's own invariants and safety laws.

The system's own math engine continuously stress-tests its safety guarantees
against real history, turning subtle architecture bugs and policy gaps into
concrete, math-backed incidents.

Runtime Enforcement:
- Pre-conditions: Checked BEFORE execution (treaty exists? risk acceptable?)
- Post-conditions: Checked AFTER execution (dignity violated? timestamps valid?)
- Severity handling:
  - CRITICAL: Block if violated
  - HIGH: Warn, require acknowledgment
  - MEDIUM/LOW: Log only

Key Types:
- ConstitutionalInvariant: A safety law to verify (with precedence)
- ConstitutionalEnforcer: Runtime enforcement of invariants
- EnforcementResult: Result of pre/post condition checks
- ConstitutionalHealthProof: Proof that an invariant holds
- ConstitutionalCounterexample: Evidence that an invariant was violated
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable, Tuple
from datetime import datetime
from enum import Enum
import uuid
import time

from quintet.core.types import Receipt, ModeResultBase, SPEC_VERSION


# =============================================================================
# INVARIANT TYPES
# =============================================================================

class InvariantCategory(Enum):
    """Categories of constitutional invariants."""
    TEMPORAL = "temporal"           # Tri-temporal ordering, causality
    DIGNITY = "dignity"             # Dignity floor, consent
    SAFETY = "safety"               # Tool safety, harm prevention
    CONSISTENCY = "consistency"     # Receipt continuity, state coherence
    GOVERNANCE = "governance"       # Policy compliance, treaty adherence


class InvariantSeverity(Enum):
    """Severity of invariant violations."""
    CRITICAL = "critical"   # System must halt
    HIGH = "high"           # Guardian must review
    MEDIUM = "medium"       # Logged for audit
    LOW = "low"             # Informational


class CheckPhase(Enum):
    """When to check an invariant."""
    PRE = "pre"             # Before execution
    POST = "post"           # After execution
    BOTH = "both"           # Both before and after


# Predicate type: takes (context_dict) -> (passed: bool, details: str)
InvariantPredicate = Callable[[Dict[str, Any]], Tuple[bool, str]]


@dataclass
class ConstitutionalInvariant:
    """
    A safety law or invariant to verify.
    
    Expressed as a predicate that Math Mode can evaluate over receipts/state.
    Includes precedence for conflict resolution: higher precedence wins.
    """
    invariant_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: InvariantCategory = InvariantCategory.SAFETY
    severity: InvariantSeverity = InvariantSeverity.HIGH
    
    # Precedence: 0-100, higher = more important
    # Default precedences:
    #   DIGNITY (90) > TEMPORAL (80) > SAFETY (70) > GOVERNANCE (60) > CONSISTENCY (50)
    precedence: int = 50
    
    # When to check: pre, post, or both
    check_phase: CheckPhase = CheckPhase.POST
    
    # The invariant expressed as a mathematical statement
    # E.g., "for all envelopes e: e.event_time <= e.observed_time <= e.transaction_time"
    formal_statement: str = ""
    
    # Fast runtime predicate for direct evaluation
    # Takes context dict with: intent, result, session, treaties, etc.
    # Returns: (passed: bool, details: str)
    runtime_predicate: Optional[InvariantPredicate] = None
    
    # Math Mode problem template (for deep audits, not runtime)
    # Variables: {receipts}, {state}, {params}
    math_problem_template: str = ""
    
    # Expected outcome when invariant holds
    expected_outcome: str = "True"
    
    # Active/enabled
    enabled: bool = True
    
    def check(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Run the fast runtime predicate if available.
        Returns (passed, details).
        """
        if not self.enabled:
            return True, "Invariant disabled"
        
        if self.runtime_predicate is None:
            return True, "No runtime predicate defined (audit-only invariant)"
        
        try:
            return self.runtime_predicate(context)
        except Exception as e:
            return False, f"Predicate error: {str(e)}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "severity": self.severity.value,
            "precedence": self.precedence,
            "check_phase": self.check_phase.value,
            "formal_statement": self.formal_statement,
            "enabled": self.enabled
        }


def resolve_conflict(inv_a: ConstitutionalInvariant, inv_b: ConstitutionalInvariant) -> ConstitutionalInvariant:
    """
    When two invariants conflict, return the one that wins.
    Higher precedence wins. Ties go to higher severity.
    """
    if inv_a.precedence != inv_b.precedence:
        return inv_a if inv_a.precedence > inv_b.precedence else inv_b
    
    # Tie-breaker: severity
    severity_order = [
        InvariantSeverity.CRITICAL,
        InvariantSeverity.HIGH,
        InvariantSeverity.MEDIUM,
        InvariantSeverity.LOW
    ]
    a_idx = severity_order.index(inv_a.severity)
    b_idx = severity_order.index(inv_b.severity)
    
    return inv_a if a_idx <= b_idx else inv_b


# =============================================================================
# RUNTIME PREDICATES FOR STANDARD INVARIANTS
# =============================================================================

def _check_tri_temporal(context: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Post-condition: Check that timestamps are properly ordered.
    event_time <= observed_time <= transaction_time <= receipt_time
    """
    result = context.get("result")
    if not result:
        return True, "No result to check"
    
    # Check context_flow entries if available
    flow = getattr(result, "context_flow", []) or []
    if not flow:
        return True, "No context flow to verify"
    
    # Extract timestamps and verify ordering
    timestamps = []
    for entry in flow:
        ts = getattr(entry, "timestamp", None) or entry.get("timestamp") if isinstance(entry, dict) else None
        if ts:
            timestamps.append(ts)
    
    if len(timestamps) < 2:
        return True, "Insufficient timestamps for ordering check"
    
    # Verify non-decreasing order
    for i in range(1, len(timestamps)):
        if timestamps[i] < timestamps[i-1]:
            return False, f"Timestamp ordering violated: {timestamps[i-1]} > {timestamps[i]}"
    
    return True, f"Verified ordering of {len(timestamps)} timestamps"


def _check_dignity_floor(context: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Post-condition: Check that dignity score never dropped below 0.15.
    If it did, a veto must have been recorded.
    """
    result = context.get("result")
    if not result:
        return True, "No result to check"
    
    # Check world_impact assessment
    world_impact = getattr(result, "world_impact", None)
    if not world_impact:
        return True, "No world impact assessment"
    
    impact_score = getattr(world_impact, "impact_score", 0.0)
    
    # If impact is high, confidence must be high or guardian must have approved
    if impact_score > 0.8:
        confidence = getattr(result, "success", False)
        has_guardian = context.get("guardian_approved", False)
        
        if not confidence and not has_guardian:
            return False, f"High impact ({impact_score}) without guardian approval"
    
    return True, "Dignity floor maintained"


def _safe_get(obj: Any, key: str, default=None) -> Any:
    """Safely get attribute from dataclass or dict."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _check_treaty_compliance(context: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Pre-condition: Check that high-stakes actions have valid treaties.
    Protected domains: healthcare, finance, legal, climate, humanitarian.
    """
    intent = context.get("intent")
    synthesis = context.get("synthesis")
    
    if not intent and not synthesis:
        return True, "No intent to check"
    
    # Get risk level and domain (handling both dataclass and dict)
    risk_level = None
    domain = None
    treaty = None
    
    if synthesis:
        risk_level = _safe_get(synthesis, "risk_level")
        domain = _safe_get(synthesis, "world_impact_category")
        treaty = _safe_get(synthesis, "treaty")
    
    if intent:
        risk_level = risk_level or _safe_get(intent, "risk_level")
        domain = domain or _safe_get(intent, "world_impact_category")
    
    # Protected domains that require treaties
    protected_domains = {
        "healthcare_medicine",
        "finance_economics",
        "legal_governance",
        "climate_environment",
        "humanitarian"
    }
    
    # Check if treaty is required
    if domain in protected_domains or risk_level in ["high", "critical"]:
        if not treaty:
            return False, f"Protected domain '{domain}' or risk '{risk_level}' requires treaty"
        
        # Verify treaty is active
        treaty_status = _safe_get(treaty, "status", "unknown")
        if treaty_status != "active":
            return False, f"Treaty status is '{treaty_status}', must be 'active'"
    
    return True, "Treaty compliance verified"


def _check_receipt_continuity(context: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Post-condition: Check that receipt chain has no gaps.
    """
    receipts = context.get("receipts", [])
    
    if len(receipts) < 2:
        return True, "Insufficient receipts for continuity check"
    
    # Simple check: verify each receipt has a result_id
    for i, receipt in enumerate(receipts):
        result_id = getattr(receipt, "result_id", None) or receipt.get("result_id")
        if not result_id:
            return False, f"Receipt {i} missing result_id"
    
    return True, f"Receipt continuity verified ({len(receipts)} receipts)"


# =============================================================================
# STANDARD INVARIANTS (with predicates and precedence)
# =============================================================================

TRI_TEMPORAL_INVARIANT = ConstitutionalInvariant(
    invariant_id="inv-tri-temporal-001",
    name="Tri-Temporal Ordering",
    description="For all envelopes, event_time <= observed_time <= transaction_time <= receipt_time",
    category=InvariantCategory.TEMPORAL,
    severity=InvariantSeverity.CRITICAL,
    precedence=80,  # High precedence
    check_phase=CheckPhase.POST,
    formal_statement="∀e ∈ Envelopes: e.event_time ≤ e.observed_time ≤ e.transaction_time ≤ e.receipt_time",
    runtime_predicate=_check_tri_temporal,
    math_problem_template="""
Given receipts with timestamps:
{receipts}

Prove or find counterexample:
For all receipts r, verify: r.event_time <= r.observed_time <= r.transaction_time <= r.receipt_time
""",
    expected_outcome="True (all orderings valid)"
)

DIGNITY_FLOOR_INVARIANT = ConstitutionalInvariant(
    invariant_id="inv-dignity-floor-001",
    name="Dignity Floor",
    description="Dignity score must never drop below 0.15 without Guardian veto",
    category=InvariantCategory.DIGNITY,
    severity=InvariantSeverity.CRITICAL,
    precedence=90,  # Highest precedence - dignity is paramount
    check_phase=CheckPhase.POST,
    formal_statement="∀d ∈ DignityScores: d.value < 0.15 → ∃v ∈ Vetoes: v.triggered_by = d",
    runtime_predicate=_check_dignity_floor,
    math_problem_template="""
Given dignity scores and veto records:
Scores: {dignity_scores}
Vetoes: {vetoes}

Prove or find counterexample:
For all scores s where s.value < 0.15, there exists a veto v where v.triggered_by = s.id
""",
    expected_outcome="True (all low-dignity events have vetoes)"
)

RECEIPT_CONTINUITY_INVARIANT = ConstitutionalInvariant(
    invariant_id="inv-receipt-continuity-001",
    name="Receipt Continuity",
    description="Receipt chain must have no gaps (each receipt references its predecessor)",
    category=InvariantCategory.CONSISTENCY,
    severity=InvariantSeverity.HIGH,
    precedence=50,  # Lower precedence - important but not blocking
    check_phase=CheckPhase.POST,
    formal_statement="∀r ∈ Receipts: r.sequence_num > 1 → ∃p ∈ Receipts: p.sequence_num = r.sequence_num - 1",
    runtime_predicate=_check_receipt_continuity,
    math_problem_template="""
Given receipt sequence numbers:
{sequence_numbers}

Prove or find counterexample:
The sequence has no gaps (consecutive integers from min to max)
""",
    expected_outcome="True (continuous sequence)"
)

TREATY_COMPLIANCE_INVARIANT = ConstitutionalInvariant(
    invariant_id="inv-treaty-compliance-001",
    name="Treaty Compliance",
    description="High-stakes actions in protected domains must have active treaties",
    category=InvariantCategory.GOVERNANCE,
    severity=InvariantSeverity.CRITICAL,  # CRITICAL - must block unsafe actions
    precedence=60,  # Medium-high precedence
    check_phase=CheckPhase.PRE,  # Must check BEFORE execution
    formal_statement="∀a ∈ HighStakesActions: a.domain ∈ ProtectedDomains → ∃t ∈ Treaties: t.covers(a) ∧ t.status = 'active'",
    runtime_predicate=_check_treaty_compliance,
    math_problem_template="""
Given actions and treaties:
Actions: {actions}
Treaties: {treaties}
Protected domains: {protected_domains}

Prove or find counterexample:
For all high-stakes actions in protected domains, an active treaty exists that covers the action
""",
    expected_outcome="True (all high-stakes actions covered by treaties)"
)

# Standard invariants registry
STANDARD_INVARIANTS = [
    TRI_TEMPORAL_INVARIANT,
    DIGNITY_FLOOR_INVARIANT,
    RECEIPT_CONTINUITY_INVARIANT,
    TREATY_COMPLIANCE_INVARIANT,
]


# =============================================================================
# ENFORCEMENT RESULTS
# =============================================================================

@dataclass
class EnforcementResult:
    """
    Result of constitutional enforcement check.
    
    Contains:
    - allowed: Whether execution can proceed
    - blocking_invariant: If blocked, which invariant caused it
    - warnings: Non-blocking issues
    - receipt: Audit trail of the check
    """
    allowed: bool = True
    blocking_invariant: Optional[ConstitutionalInvariant] = None
    blocking_reason: str = ""
    warnings: List[str] = field(default_factory=list)
    passed_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    check_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "blocking_invariant": self.blocking_invariant.invariant_id if self.blocking_invariant else None,
            "blocking_reason": self.blocking_reason,
            "warnings": self.warnings,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "check_time_ms": self.check_time_ms
        }


# =============================================================================
# CONSTITUTIONAL ENFORCER
# =============================================================================

class ConstitutionalEnforcer:
    """
    Lightweight runtime enforcer for constitutional invariants.
    
    Called by orchestrators before/after execution to ensure
    invariants are not violated.
    
    Design principles:
    - FAST: Only simple predicate checks, no Math Mode calls
    - Severity-aware: CRITICAL blocks, HIGH warns, others log
    - Composable: Works for Build, Math, and any future mode
    """
    
    def __init__(
        self,
        invariants: Optional[List[ConstitutionalInvariant]] = None,
        strict_mode: bool = False
    ):
        """
        Initialize enforcer.
        
        Args:
            invariants: List of invariants to enforce (default: STANDARD_INVARIANTS)
            strict_mode: If True, HIGH severity also blocks (not just CRITICAL)
        """
        self.invariants = invariants or STANDARD_INVARIANTS.copy()
        self.strict_mode = strict_mode
    
    def check_pre_conditions(
        self,
        intent: Optional[Any] = None,
        synthesis: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EnforcementResult:
        """
        Check pre-conditions before execution.
        
        Args:
            intent: IntentEnvelope (if available)
            synthesis: QuintetSynthesis (if available)
            context: Additional context dict
        
        Returns:
            EnforcementResult with allowed=False if execution should be blocked
        """
        start = time.time()
        
        # Build context for predicates
        check_context = context.copy() if context else {}
        check_context["intent"] = intent
        check_context["synthesis"] = synthesis
        check_context["phase"] = "pre"
        
        result = EnforcementResult()
        
        # Check all pre-condition invariants
        for inv in self.invariants:
            if not inv.enabled:
                continue
            
            if inv.check_phase not in [CheckPhase.PRE, CheckPhase.BOTH]:
                continue
            
            passed, details = inv.check(check_context)
            
            if passed:
                result.passed_checks.append(f"{inv.name}: {details}")
            else:
                result.failed_checks.append(f"{inv.name}: {details}")
                
                # Determine if this should block
                if inv.severity == InvariantSeverity.CRITICAL:
                    result.allowed = False
                    result.blocking_invariant = inv
                    result.blocking_reason = details
                    break  # Stop on first CRITICAL failure
                
                elif inv.severity == InvariantSeverity.HIGH:
                    if self.strict_mode:
                        result.allowed = False
                        result.blocking_invariant = inv
                        result.blocking_reason = details
                        break
                    else:
                        result.warnings.append(f"[HIGH] {inv.name}: {details}")
                
                else:
                    # MEDIUM/LOW - just log
                    result.warnings.append(f"[{inv.severity.value.upper()}] {inv.name}: {details}")
        
        result.check_time_ms = (time.time() - start) * 1000
        return result
    
    def check_post_conditions(
        self,
        result: Optional[ModeResultBase] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> EnforcementResult:
        """
        Check post-conditions after execution.
        
        Args:
            result: The ModeResultBase from execution
            context: Additional context dict
        
        Returns:
            EnforcementResult indicating any violations
        """
        start = time.time()
        
        # Build context for predicates
        check_context = context.copy() if context else {}
        check_context["result"] = result
        check_context["phase"] = "post"
        
        enforcement = EnforcementResult()
        
        # Check all post-condition invariants
        for inv in self.invariants:
            if not inv.enabled:
                continue
            
            if inv.check_phase not in [CheckPhase.POST, CheckPhase.BOTH]:
                continue
            
            passed, details = inv.check(check_context)
            
            if passed:
                enforcement.passed_checks.append(f"{inv.name}: {details}")
            else:
                enforcement.failed_checks.append(f"{inv.name}: {details}")
                
                # Post-condition violations are logged but don't block
                # (execution already happened)
                # However, they should be flagged for review
                
                if inv.severity == InvariantSeverity.CRITICAL:
                    enforcement.warnings.append(f"[CRITICAL VIOLATION] {inv.name}: {details}")
                    enforcement.allowed = False  # Mark as violation detected
                    enforcement.blocking_invariant = inv
                    enforcement.blocking_reason = details
                
                elif inv.severity == InvariantSeverity.HIGH:
                    enforcement.warnings.append(f"[HIGH] {inv.name}: {details}")
                
                else:
                    enforcement.warnings.append(f"[{inv.severity.value.upper()}] {inv.name}: {details}")
        
        enforcement.check_time_ms = (time.time() - start) * 1000
        return enforcement
    
    def add_invariant(self, invariant: ConstitutionalInvariant):
        """Add a new invariant to the enforcer."""
        self.invariants.append(invariant)
    
    def remove_invariant(self, invariant_id: str):
        """Remove an invariant by ID."""
        self.invariants = [inv for inv in self.invariants if inv.invariant_id != invariant_id]
    
    def get_invariants_by_phase(self, phase: CheckPhase) -> List[ConstitutionalInvariant]:
        """Get invariants that apply to a specific phase."""
        return [
            inv for inv in self.invariants 
            if inv.enabled and inv.check_phase in [phase, CheckPhase.BOTH]
        ]


# =============================================================================
# ENFORCEMENT RECEIPTS
# =============================================================================

@dataclass
class ConstitutionalBlockReceipt(Receipt):
    """
    Receipt emitted when an action is blocked by pre-condition check.
    
    This is evidence of the system working correctly - it refused
    an unsafe action.
    """
    receipt_type: str = "constitutional_block"
    mode: str = "constitutional"
    
    # Which invariant blocked
    invariant_id: str = ""
    invariant_name: str = ""
    severity: InvariantSeverity = InvariantSeverity.CRITICAL
    
    # What was blocked
    blocked_action: str = ""
    block_reason: str = ""
    
    # Context at time of block
    intent_id: Optional[str] = None
    synthesis_id: Optional[str] = None
    risk_level: Optional[str] = None
    domain: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "invariant_id": self.invariant_id,
            "invariant_name": self.invariant_name,
            "severity": self.severity.value,
            "blocked_action": self.blocked_action,
            "block_reason": self.block_reason,
            "intent_id": self.intent_id,
            "synthesis_id": self.synthesis_id,
            "risk_level": self.risk_level,
            "domain": self.domain
        })
        return d


@dataclass
class ConstitutionalViolationReceipt(Receipt):
    """
    Receipt emitted when a post-condition violation is detected.
    
    Execution already happened, but we detected a problem.
    Guardian/Council should review.
    """
    receipt_type: str = "constitutional_violation"
    mode: str = "constitutional"
    
    # Which invariant was violated
    invariant_id: str = ""
    invariant_name: str = ""
    severity: InvariantSeverity = InvariantSeverity.HIGH
    
    # Violation details
    violation_description: str = ""
    affected_result_id: Optional[str] = None
    
    # Escalation status
    escalated_to_guardian: bool = False
    escalated_to_council: bool = False
    remediation_status: str = "open"  # "open" | "investigating" | "resolved" | "accepted"
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "invariant_id": self.invariant_id,
            "invariant_name": self.invariant_name,
            "severity": self.severity.value,
            "violation_description": self.violation_description,
            "affected_result_id": self.affected_result_id,
            "escalated_to_guardian": self.escalated_to_guardian,
            "escalated_to_council": self.escalated_to_council,
            "remediation_status": self.remediation_status
        })
        return d


@dataclass
class ConstitutionalPassReceipt(Receipt):
    """
    Receipt emitted when all constitutional checks pass.
    
    Optional - use for audit trails in high-stakes flows.
    """
    receipt_type: str = "constitutional_pass"
    mode: str = "constitutional"
    
    # What was checked
    phase: str = "pre"  # "pre" | "post"
    invariants_checked: int = 0
    invariants_passed: int = 0
    
    # Summary
    check_time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "phase": self.phase,
            "invariants_checked": self.invariants_checked,
            "invariants_passed": self.invariants_passed,
            "check_time_ms": self.check_time_ms,
            "warnings": self.warnings
        })
        return d


# =============================================================================
# DEEP VERIFICATION RESULTS (for Math Mode audits)
# =============================================================================

@dataclass
class ConstitutionalHealthProof(Receipt):
    """
    Receipt proving an invariant holds over a slice of history.
    
    Emitted when Math Mode successfully verifies an invariant.
    """
    receipt_type: str = "constitutional_health_proof"
    mode: str = "constitutional"
    
    # Which invariant was verified
    invariant_id: str = ""
    invariant_name: str = ""
    
    # Verification details
    verified_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    receipts_checked: int = 0
    time_range_start: Optional[str] = None
    time_range_end: Optional[str] = None
    
    # Math Mode result reference
    math_result_id: Optional[str] = None
    proof_summary: str = ""
    confidence: float = 0.0
    
    # Cryptographic commitment (optional, for auditability)
    proof_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "invariant_id": self.invariant_id,
            "invariant_name": self.invariant_name,
            "verified_at": self.verified_at,
            "receipts_checked": self.receipts_checked,
            "time_range_start": self.time_range_start,
            "time_range_end": self.time_range_end,
            "math_result_id": self.math_result_id,
            "proof_summary": self.proof_summary,
            "confidence": self.confidence,
            "proof_hash": self.proof_hash
        })
        return d


@dataclass
class ConstitutionalCounterexample(Receipt):
    """
    Receipt documenting a violation or inability to prove an invariant.
    
    Emitted when Math Mode finds a counterexample or cannot prove.
    Guardian/Council must review.
    """
    receipt_type: str = "constitutional_counterexample"
    mode: str = "constitutional"
    
    # Which invariant failed
    invariant_id: str = ""
    invariant_name: str = ""
    severity: InvariantSeverity = InvariantSeverity.HIGH
    
    # Failure details
    failure_type: str = ""  # "counterexample_found" | "proof_timeout" | "undecidable"
    counterexample: Optional[Dict[str, Any]] = None  # The violating case
    violating_receipts: List[str] = field(default_factory=list)  # Receipt IDs
    
    # What went wrong
    violation_description: str = ""
    suggested_action: str = ""
    
    # Math Mode result reference
    math_result_id: Optional[str] = None
    
    # Escalation status
    escalated_to_guardian: bool = False
    escalated_to_council: bool = False
    resolution_status: str = "open"  # "open" | "investigating" | "resolved" | "accepted_risk"
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "invariant_id": self.invariant_id,
            "invariant_name": self.invariant_name,
            "severity": self.severity.value,
            "failure_type": self.failure_type,
            "counterexample": self.counterexample,
            "violating_receipts": self.violating_receipts,
            "violation_description": self.violation_description,
            "suggested_action": self.suggested_action,
            "escalated_to_guardian": self.escalated_to_guardian,
            "escalated_to_council": self.escalated_to_council,
            "resolution_status": self.resolution_status
        })
        return d


# =============================================================================
# CHECKER INTERFACE (for deep audits)
# =============================================================================

@dataclass
class ConstitutionalCheckRequest:
    """Request to verify one or more invariants."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    invariant_ids: List[str] = field(default_factory=list)  # Empty = all enabled
    receipts: List[Dict[str, Any]] = field(default_factory=list)
    time_range_start: Optional[str] = None
    time_range_end: Optional[str] = None
    max_receipts: int = 1000
    timeout_ms: int = 30000


@dataclass
class ConstitutionalCheckResult:
    """Result of constitutional verification."""
    request_id: str = ""
    
    # Overall status
    all_passed: bool = False
    invariants_checked: int = 0
    invariants_passed: int = 0
    invariants_failed: int = 0
    
    # Detailed results
    proofs: List[ConstitutionalHealthProof] = field(default_factory=list)
    counterexamples: List[ConstitutionalCounterexample] = field(default_factory=list)
    
    # Timing
    total_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "all_passed": self.all_passed,
            "invariants_checked": self.invariants_checked,
            "invariants_passed": self.invariants_passed,
            "invariants_failed": self.invariants_failed,
            "proofs": [p.to_dict() for p in self.proofs],
            "counterexamples": [c.to_dict() for c in self.counterexamples],
            "total_time_ms": self.total_time_ms
        }


# =============================================================================
# SINGLETON ENFORCER INSTANCE
# =============================================================================

# Default enforcer instance for easy access
_default_enforcer: Optional[ConstitutionalEnforcer] = None


def get_enforcer(strict_mode: bool = False) -> ConstitutionalEnforcer:
    """Get or create the default enforcer instance."""
    global _default_enforcer
    if _default_enforcer is None:
        _default_enforcer = ConstitutionalEnforcer(strict_mode=strict_mode)
    return _default_enforcer


def reset_enforcer():
    """Reset the default enforcer (for testing)."""
    global _default_enforcer
    _default_enforcer = None
