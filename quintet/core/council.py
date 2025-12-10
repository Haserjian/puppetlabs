"""
Quintet Council Types & Contracts
==================================

This module defines the Quintet multi-agent council layer that sits
above Ultra Mode and Math Mode.

Decision Flow:
  UserIntent → QuintetDeliberation → (Ultra/Math)Action → Receipts → Learning

The council is the "intent shaper" that transforms user requests into
structured synthesis objects that Ultra Mode and Math Mode can execute.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Literal
from datetime import datetime
from enum import Enum
import uuid

from quintet.core.types import SPEC_VERSION, Receipt


# =============================================================================
# AGENT ROLES
# =============================================================================

class AgentRole(Enum):
    """Quintet council agent roles."""
    ALPHA = "alpha"     # Strategic oversight, risk assessment
    BETA = "beta"       # Technical execution, feasibility
    GAMMA = "gamma"     # Ethical/safety review, world-impact
    DELTA = "delta"     # Resource/time optimization
    EPSILON = "epsilon" # Synthesis, conflict resolution


@dataclass
class AgentVote:
    """Single agent's vote/opinion on a decision."""
    agent: AgentRole
    position: str               # "approve" | "reject" | "defer" | "modify"
    confidence: float           # 0.0-1.0
    rationale: str
    concerns: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)  # Receipt/proof IDs
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent.value,
            "position": self.position,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "concerns": self.concerns,
            "suggestions": self.suggestions,
            "evidence_refs": self.evidence_refs
        }


# =============================================================================
# INTENT ENVELOPE
# =============================================================================

@dataclass
class IntentEnvelope:
    """
    The single "slot" where human/council intent is structured.
    
    Every meaningful action in Quintet originates from an IntentEnvelope.
    This is the "programming is intent" principle made concrete.
    """
    intent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # What the user/system wants
    raw_query: str = ""
    proposed_action: str = ""
    goal: str = ""
    
    # Context and constraints
    rationale: str = ""
    constraints: List[str] = field(default_factory=list)
    invariants: List[str] = field(default_factory=list)  # Must never be violated
    
    # Risk assessment
    risk_level: str = "low"     # "low" | "medium" | "high" | "critical"
    world_impact_category: Optional[str] = None
    
    # Mode routing hints
    requires_build: bool = False
    requires_math: bool = False
    allowed_modes: List[str] = field(default_factory=lambda: ["build", "math"])
    
    # Open questions (things to resolve before acting)
    open_questions: List[str] = field(default_factory=list)
    
    # Provenance
    source: str = "user"        # "user" | "council" | "system"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "raw_query": self.raw_query,
            "proposed_action": self.proposed_action,
            "goal": self.goal,
            "rationale": self.rationale,
            "constraints": self.constraints,
            "invariants": self.invariants,
            "risk_level": self.risk_level,
            "world_impact_category": self.world_impact_category,
            "requires_build": self.requires_build,
            "requires_math": self.requires_math,
            "allowed_modes": self.allowed_modes,
            "open_questions": self.open_questions,
            "source": self.source,
            "created_at": self.created_at
        }


# =============================================================================
# TREATY (for high-stakes flows)
# =============================================================================

@dataclass
class TreatyParty:
    """A party to a treaty (user, agent, regulator, system)."""
    party_id: str
    party_type: str             # "user" | "agent" | "guardian" | "regulator" | "system"
    role: str                   # Their role in this treaty
    obligations: List[str] = field(default_factory=list)
    rights: List[str] = field(default_factory=list)


@dataclass
class Treaty:
    """
    Formal agreement for high-stakes flows (clinical, finance, governance).
    
    Guardian refuses actions in treaty-protected domains unless a valid
    treaty instance is present and consistent.
    """
    treaty_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    
    # Parties and their roles
    parties: List[TreatyParty] = field(default_factory=list)
    
    # Guarantees this treaty provides
    guarantees: List[str] = field(default_factory=list)
    
    # Required receipts/artifacts
    required_receipts: List[str] = field(default_factory=list)
    required_validations: List[str] = field(default_factory=list)
    
    # Veto rules
    veto_conditions: List[str] = field(default_factory=list)
    veto_parties: List[str] = field(default_factory=list)  # Who can veto
    
    # Scope
    domains: List[str] = field(default_factory=list)  # "healthcare", "finance", etc.
    expiry: Optional[str] = None  # ISO datetime or None for permanent
    
    # Status
    status: str = "active"      # "draft" | "active" | "suspended" | "expired"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "treaty_id": self.treaty_id,
            "name": self.name,
            "parties": [
                {"party_id": p.party_id, "party_type": p.party_type, "role": p.role}
                for p in self.parties
            ],
            "guarantees": self.guarantees,
            "required_receipts": self.required_receipts,
            "veto_conditions": self.veto_conditions,
            "domains": self.domains,
            "status": self.status
        }


# =============================================================================
# QUINTET SYNTHESIS
# =============================================================================

@dataclass
class QuintetSynthesis:
    """
    The output of Quintet council deliberation.
    
    This is the contract between Quintet and Ultra Mode / Math Mode.
    Both modes accept this same structure.
    """
    synthesis_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # The structured intent
    intent: Optional[IntentEnvelope] = None
    
    # Council decision
    decision: str = "proceed"   # "proceed" | "reject" | "defer" | "escalate"
    confidence: float = 0.0
    
    # Agent votes
    votes: List[AgentVote] = field(default_factory=list)
    dissent: bool = False       # True if agents disagreed
    dissent_summary: Optional[str] = None
    
    # Action routing
    proposed_action: str = ""
    requires_build: bool = False
    requires_math: bool = False
    primary_mode: Optional[str] = None  # "build" | "math" | None
    
    # Risk and guardrails
    risk_level: str = "low"
    world_impact_category: Optional[str] = None
    guardrails: List[str] = field(default_factory=list)
    
    # Treaty (if high-stakes)
    treaty: Optional[Treaty] = None
    
    # Open questions for modes to address
    open_questions: List[str] = field(default_factory=list)
    
    # Evidence used in deliberation
    evidence_refs: List[str] = field(default_factory=list)  # Receipt/proof IDs
    
    # Timing
    deliberation_time_ms: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "synthesis_id": self.synthesis_id,
            "intent": self.intent.to_dict() if self.intent else None,
            "decision": self.decision,
            "confidence": self.confidence,
            "votes": [v.to_dict() for v in self.votes],
            "dissent": self.dissent,
            "dissent_summary": self.dissent_summary,
            "proposed_action": self.proposed_action,
            "requires_build": self.requires_build,
            "requires_math": self.requires_math,
            "primary_mode": self.primary_mode,
            "risk_level": self.risk_level,
            "world_impact_category": self.world_impact_category,
            "guardrails": self.guardrails,
            "treaty": self.treaty.to_dict() if self.treaty else None,
            "open_questions": self.open_questions,
            "evidence_refs": self.evidence_refs,
            "deliberation_time_ms": self.deliberation_time_ms,
            "created_at": self.created_at
        }


# =============================================================================
# COUNCIL RECEIPTS
# =============================================================================

@dataclass
class CouncilDecisionReceipt(Receipt):
    """
    Receipt for a Quintet council decision.
    
    Embeds the full synthesis so the decision can be audited.
    """
    receipt_type: str = "council_decision"
    mode: str = "quintet"
    
    synthesis: Optional[QuintetSynthesis] = None
    
    # What happened next
    delegated_to: Optional[str] = None  # "build" | "math" | None
    delegated_result_id: Optional[str] = None
    
    # Outcome
    outcome: str = "pending"    # "pending" | "success" | "failure" | "escalated"
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "synthesis": self.synthesis.to_dict() if self.synthesis else None,
            "delegated_to": self.delegated_to,
            "delegated_result_id": self.delegated_result_id,
            "outcome": self.outcome
        })
        return d


@dataclass
class DesignDecisionReceipt(Receipt):
    """
    Receipt for design/abstraction decisions.
    
    Logs when and why we move between:
    - Raw prompts ↔ structured DSL
    - Visual UI ↔ textual spec
    - LLM output ↔ hand-written code
    """
    receipt_type: str = "design_decision"
    mode: str = "system"
    
    # What changed
    decision_type: str = ""     # "abstraction_shift" | "llm_usage" | "manual_override"
    from_state: str = ""        # e.g., "llm_draft", "prompt_driven"
    to_state: str = ""          # e.g., "hand_written", "dsl_driven"
    
    # Why
    rationale: str = ""
    risk_assessment: Optional[str] = None
    
    # Context
    artifact_path: Optional[str] = None
    artifact_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "decision_type": self.decision_type,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "rationale": self.rationale,
            "risk_assessment": self.risk_assessment,
            "artifact_path": self.artifact_path
        })
        return d


# =============================================================================
# SESSION CONTEXT
# =============================================================================

@dataclass
class SessionContext:
    """
    Per-session state shared by Quintet, Ultra Mode, and Math Mode.
    
    Maintains continuity across multi-step interactions.
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Session configuration
    mode: str = "standard"      # "standard" | "high_stakes" | "investigation"
    
    # History
    intents: List[IntentEnvelope] = field(default_factory=list)
    decisions: List[QuintetSynthesis] = field(default_factory=list)
    result_ids: List[str] = field(default_factory=list)
    
    # Accumulated knowledge
    discovered_facts: List[str] = field(default_factory=list)
    discovered_lemmas: List[str] = field(default_factory=list)  # For Math Mode
    active_constraints: List[str] = field(default_factory=list)
    
    # Session-level risk
    cumulative_risk: str = "low"
    treaties_active: List[str] = field(default_factory=list)  # Treaty IDs
    
    # Timing
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def add_intent(self, intent: IntentEnvelope):
        """Add an intent to the session history."""
        self.intents.append(intent)
        self.last_activity = datetime.utcnow().isoformat()
    
    def add_decision(self, synthesis: QuintetSynthesis):
        """Add a council decision to the session history."""
        self.decisions.append(synthesis)
        self.last_activity = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "intent_count": len(self.intents),
            "decision_count": len(self.decisions),
            "discovered_facts": self.discovered_facts,
            "discovered_lemmas": self.discovered_lemmas,
            "cumulative_risk": self.cumulative_risk,
            "treaties_active": self.treaties_active,
            "started_at": self.started_at,
            "last_activity": self.last_activity
        }


# =============================================================================
# MODE ARBITRATION POLICY
# =============================================================================

@dataclass
class ArbitrationPolicy:
    """
    Policy for deciding when council runs vs direct routing.
    
    High-risk/high-impact → Quintet council first
    Low-risk/local → Router can go directly to Build/Math
    """
    # Risk thresholds
    council_required_risk_levels: List[str] = field(
        default_factory=lambda: ["high", "critical"]
    )
    
    # Domain triggers (always require council)
    council_required_domains: List[str] = field(
        default_factory=lambda: [
            "healthcare_medicine",
            "finance_economics", 
            "legal_governance",
            "climate_environment",
            "humanitarian"
        ]
    )
    
    # Bypass conditions (router can skip council)
    bypass_allowed: bool = True
    bypass_max_risk: str = "medium"
    bypass_confidence_threshold: float = 0.8
    
    # Always log even when bypassing
    always_emit_receipts: bool = True
    
    def requires_council(
        self,
        risk_level: str,
        domain: Optional[str],
        confidence: float
    ) -> bool:
        """Determine if this request requires council deliberation."""
        # High risk always needs council
        if risk_level in self.council_required_risk_levels:
            return True
        
        # Certain domains always need council
        if domain and domain in self.council_required_domains:
            return True
        
        # Low confidence needs council review
        if confidence < self.bypass_confidence_threshold:
            return True
        
        # Otherwise, can bypass if allowed
        return not self.bypass_allowed


# =============================================================================
# CANONICAL JSON EXAMPLES
# =============================================================================

EXAMPLE_SYNTHESIS_HIGH_STAKES = {
    "synthesis_id": "syn-001",
    "intent": {
        "intent_id": "int-001",
        "raw_query": "Optimize drug dosage for patient cohort and generate deployment code",
        "proposed_action": "Mathematical optimization + code generation",
        "goal": "Find optimal dosage parameters and create safe deployment pipeline",
        "constraints": ["Must not exceed max safe dose", "Must handle edge cases"],
        "invariants": ["Patient safety > optimization accuracy"],
        "risk_level": "critical",
        "world_impact_category": "healthcare_medicine",
        "requires_build": True,
        "requires_math": True,
        "source": "user"
    },
    "decision": "proceed",
    "confidence": 0.85,
    "votes": [
        {"agent": "alpha", "position": "approve", "confidence": 0.9, "rationale": "Clear benefit, manageable risk"},
        {"agent": "beta", "position": "approve", "confidence": 0.85, "rationale": "Technically feasible"},
        {"agent": "gamma", "position": "modify", "confidence": 0.75, "rationale": "Need additional safety checks",
         "concerns": ["Edge case handling unclear"]},
        {"agent": "delta", "position": "approve", "confidence": 0.9, "rationale": "Resources available"},
        {"agent": "epsilon", "position": "approve", "confidence": 0.85, "rationale": "Consensus with Gamma's caveat"}
    ],
    "dissent": True,
    "dissent_summary": "Gamma requests additional safety validation before deployment",
    "requires_build": True,
    "requires_math": True,
    "primary_mode": "math",
    "risk_level": "critical",
    "world_impact_category": "healthcare_medicine",
    "guardrails": [
        "Math Mode must achieve 0.95 confidence",
        "Build Mode must include safety tests",
        "Guardian must review before execution"
    ],
    "treaty": {
        "treaty_id": "treaty-med-001",
        "name": "Healthcare Deployment Treaty",
        "guarantees": ["No deployment without validation", "All outputs logged"],
        "required_receipts": ["math_validation", "build_validation", "guardian_approval"],
        "domains": ["healthcare_medicine"]
    }
}

EXAMPLE_SYNTHESIS_LOW_STAKES = {
    "synthesis_id": "syn-002",
    "intent": {
        "intent_id": "int-002",
        "raw_query": "Add a helper script to clean old log files",
        "proposed_action": "Create cleanup script",
        "goal": "Automate log cleanup",
        "constraints": ["Don't delete recent logs"],
        "risk_level": "low",
        "requires_build": True,
        "requires_math": False,
        "source": "user"
    },
    "decision": "proceed",
    "confidence": 0.95,
    "votes": [],  # Council bypassed for low-stakes
    "dissent": False,
    "requires_build": True,
    "requires_math": False,
    "primary_mode": "build",
    "risk_level": "low",
    "guardrails": ["Standard validation"],
    "treaty": None  # No treaty needed
}


