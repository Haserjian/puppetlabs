"""
Phase 2 Test Episode Fixtures

Provides test episode definitions and utility functions for live integration testing.
These episodes are used by Phase 2 validation to test:
- Live call path (Invariant 5)
- Policy effect (Invariant 6)
- Failure modes (Invariant 7)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class TestEpisode:
    """A test episode definition for Phase 2 validation."""
    episode_id: str
    intent: str
    mode: str = "test"
    domain: str = "validation"
    test_marker: str = ""
    require_quintet: bool = False
    baseline_episode_id: Optional[str] = None
    custom_fields: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result = {
            "intent": self.intent,
            "mode": self.mode,
            "domain": self.domain,
            "test_marker": self.test_marker,
        }
        if self.require_quintet:
            result["require_quintet"] = True
        if self.baseline_episode_id:
            result["baseline_episode_id"] = self.baseline_episode_id
        if self.custom_fields:
            result.update(self.custom_fields)
        return result


# ============================================================================
# Invariant 5: Live Path Test Episodes
# ============================================================================

LIVE_PATH_BASELINE = TestEpisode(
    episode_id="phase2-live-path-baseline",
    intent="test_policy_evaluation",
    mode="test",
    domain="validation",
    test_marker="phase2_live_path_check",
)

LIVE_PATH_EPISODES = [LIVE_PATH_BASELINE]


# ============================================================================
# Invariant 6: Policy Effect Test Episodes
# ============================================================================

POLICY_EFFECT_BASELINE = TestEpisode(
    episode_id="phase2-policy-effect-baseline",
    intent="policy_effect_baseline",
    mode="test",
    domain="validation",
    test_marker="phase2_policy_effect_baseline",
)

POLICY_EFFECT_CHANGED = TestEpisode(
    episode_id="phase2-policy-effect-changed",
    intent="policy_effect_changed",
    mode="test",
    domain="validation",
    test_marker="phase2_policy_effect_changed",
    baseline_episode_id=POLICY_EFFECT_BASELINE.episode_id,
)

POLICY_EFFECT_EPISODES = [POLICY_EFFECT_BASELINE, POLICY_EFFECT_CHANGED]


# ============================================================================
# Invariant 7: Failure Mode Test Episodes
# ============================================================================

FAILURE_MODE_TEST = TestEpisode(
    episode_id="phase2-failure-mode",
    intent="failure_mode_test",
    mode="test",
    domain="validation",
    test_marker="phase2_failure_mode",
    require_quintet=True,  # Explicitly require Quintet
)

FAILURE_MODE_EPISODES = [FAILURE_MODE_TEST]


# ============================================================================
# Test Policy Changes
# ============================================================================

# Safe, observable policy changes for testing
TEST_POLICY_CHANGES = {
    "brain_temperature": {
        "change": {"brain_temperature": 0.8},
        "description": "Increase brain temperature from 0.7 to 0.8",
        "expected_direction": "increase_confidence",
    },
    "brain_temperature_decrease": {
        "change": {"brain_temperature": 0.5},
        "description": "Decrease brain temperature from 0.7 to 0.5",
        "expected_direction": "decrease_confidence",
    },
    "guardian_strictness": {
        "change": {"guardian_strictness": "strict"},
        "description": "Increase guardian strictness",
        "expected_direction": "decrease_throughput",
    },
}


# ============================================================================
# Configuration Profiles
# ============================================================================

LOOM_TEST_PROFILE = {
    "daemon": {
        "port": 8765,  # Non-standard port to avoid conflicts
        "mode": "test",
        "log_level": "debug",
    },
    "quintet": {
        "service_url": "http://localhost:9000",
        "timeout_sec": 5,
        "retry_policy": "none",  # Fail fast on error
    },
}

QUINTET_TEST_PROFILE = {
    "port": 9000,
    "ephemeral": True,  # Don't persist receipts
    "validation_mode": True,  # Emit extra diagnostics
    "shadow_mode": True,  # Enable shadow execution
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_all_test_episodes() -> List[TestEpisode]:
    """Get all test episodes for Phase 2 validation."""
    return LIVE_PATH_EPISODES + POLICY_EFFECT_EPISODES + FAILURE_MODE_EPISODES


def get_episodes_for_invariant(invariant: int) -> List[TestEpisode]:
    """Get test episodes for a specific invariant."""
    invariants = {
        5: LIVE_PATH_EPISODES,
        6: POLICY_EFFECT_EPISODES,
        7: FAILURE_MODE_EPISODES,
    }
    return invariants.get(invariant, [])


def get_safe_policy_change(change_type: str = "brain_temperature") -> Dict[str, Any]:
    """Get a safe test policy change."""
    return TEST_POLICY_CHANGES.get(
        change_type,
        {"change": {"brain_temperature": 0.8}, "description": "Default safe change"},
    )
