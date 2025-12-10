"""
Quintet Core - Shared Types, Router, and Council
==================================================

This module is the SINGLE SOURCE OF TRUTH for:
- Shared types (ValidationResult, ColorTileGrid, etc.)
- Router (UltraModeRouter)
- Council contracts (IntentEnvelope, QuintetSynthesis, Treaty)

Both Build Mode and Math Mode import from here.
DO NOT duplicate these types elsewhere.
"""

from quintet.core.types import (
    # Version
    SPEC_VERSION,

    # Error handling
    ErrorCode,
    ModeError,

    # Validation
    ValidationCheck,
    ValidationResult,

    # Context & Cognition
    ContextFlowEntry,
    CognitionSummary,
    IncompletenessAssessment,
    WorldImpactAssessment,

    # Color Tiles
    ColorTile,
    ColorTileGrid,

    # Base Result
    ModeResultBase,
    Mode,

    # Resources
    ResourceLimits,
    RESOURCE_LIMITS,

    # Receipts
    Receipt,

    # Episode
    Episode,
    compute_trust_score,
    append_episode,

    # Stress / Survival
    StressLevel,
    StressProfile,
    SurvivalOutcome,
    SurvivalReceipt,
    PromotionPolicy,
)

from quintet.core.router import (
    UltraModeRouter,
    RouterDecision,
)

from quintet.core.council import (
    # Agent roles
    AgentRole,
    AgentVote,
    
    # Intent & Treaty
    IntentEnvelope,
    Treaty,
    TreatyParty,
    
    # Council output
    QuintetSynthesis,
    
    # Receipts
    CouncilDecisionReceipt,
    DesignDecisionReceipt,
    
    # Session
    SessionContext,
    
    # Policy
    ArbitrationPolicy,
)

from quintet.core.constitutional import (
    # Invariant types
    InvariantCategory,
    InvariantSeverity,
    ConstitutionalInvariant,

    # Verification results
    ConstitutionalHealthProof,
    ConstitutionalCounterexample,

    # Standard invariants
    TRI_TEMPORAL_INVARIANT,
    DIGNITY_FLOOR_INVARIANT,
    RECEIPT_CONTINUITY_INVARIANT,
    TREATY_COMPLIANCE_INVARIANT,
    STANDARD_INVARIANTS,

    # Checker interface
    ConstitutionalCheckRequest,
    ConstitutionalCheckResult,
)

from quintet.core.debate import (
    # Debate types
    DebateRole,
    Verdict,
    DebateMove,
    DebateResult,

    # Agents
    Proposer,
    Critic,
    Judge,

    # Loop
    DebateLoop,
    create_debate_loop,
    DebateConfig,
)

from quintet.core.probabilistic_detector import (
    # Classification
    ClassificationResult,
    TrainingExample,
    ProbabilisticDetector,

    # Utilities
    train_detector_from_episodes,
    load_episodes_from_jsonl,
    create_pretrained_detector,
)

__all__ = [
    # Types
    "SPEC_VERSION",
    "ErrorCode",
    "ModeError",
    "ValidationCheck",
    "ValidationResult",
    "ContextFlowEntry",
    "CognitionSummary",
    "IncompletenessAssessment",
    "WorldImpactAssessment",
    "ColorTile",
    "ColorTileGrid",
    "ModeResultBase",
    "Mode",
    "ResourceLimits",
    "RESOURCE_LIMITS",
    "Receipt",

    # Episode
    "Episode",
    "compute_trust_score",
    "append_episode",

    # Stress / Survival
    "StressLevel",
    "StressProfile",
    "SurvivalOutcome",
    "SurvivalReceipt",
    "PromotionPolicy",

    # Router
    "UltraModeRouter",
    "RouterDecision",
    
    # Council
    "AgentRole",
    "AgentVote",
    "IntentEnvelope",
    "Treaty",
    "TreatyParty",
    "QuintetSynthesis",
    "CouncilDecisionReceipt",
    "DesignDecisionReceipt",
    "SessionContext",
    "ArbitrationPolicy",
    
    # Constitutional
    "InvariantCategory",
    "InvariantSeverity",
    "ConstitutionalInvariant",
    "ConstitutionalHealthProof",
    "ConstitutionalCounterexample",
    "TRI_TEMPORAL_INVARIANT",
    "DIGNITY_FLOOR_INVARIANT",
    "RECEIPT_CONTINUITY_INVARIANT",
    "TREATY_COMPLIANCE_INVARIANT",
    "STANDARD_INVARIANTS",
    "ConstitutionalCheckRequest",
    "ConstitutionalCheckResult",

    # Debate
    "DebateRole",
    "Verdict",
    "DebateMove",
    "DebateResult",
    "Proposer",
    "Critic",
    "Judge",
    "DebateLoop",
    "create_debate_loop",
    "DebateConfig",

    # Probabilistic Detector
    "ClassificationResult",
    "TrainingExample",
    "ProbabilisticDetector",
    "train_detector_from_episodes",
    "load_episodes_from_jsonl",
    "create_pretrained_detector",
]

