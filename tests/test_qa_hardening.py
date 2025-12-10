"""
QA Hardening Tests
==================

Tests for:
- Budget enforcement (token limits, call limits)
- Timeout enforcement
- High-risk domain restrictions
- Stress profiles and survival contracts
- Promotion policies
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Router and exceptions
from quintet.model import (
    ModelRouter,
    ModelConfig,
    ModelSlotConfig,
    ModelRequest,
    ModelResponse,
    ModelRole,
    Message,
    ModelCallPolicyError,
    ModelTimeoutError,
    TokenBudgetExceededError,
    HighRiskDomainError,
)

# Core types
from quintet.core import (
    StressLevel,
    StressProfile,
    SurvivalOutcome,
    SurvivalReceipt,
    PromotionPolicy,
    Receipt,
)


# =============================================================================
# MOCK BACKEND
# =============================================================================

class MockBackend:
    """Mock backend for testing."""

    def __init__(self, response_text: str = "mock response", delay_ms: float = 0):
        self.response_text = response_text
        self.delay_ms = delay_ms
        self.calls = []

    async def complete(self, req: ModelRequest) -> ModelResponse:
        self.calls.append(req)
        if self.delay_ms > 0:
            await asyncio.sleep(self.delay_ms / 1000.0)
        return ModelResponse(
            text=self.response_text,
            provider="mock",
            model_id="mock-model",
            tokens_in=10,
            tokens_out=20,
            cost_estimate_usd=0.001,
        )


# =============================================================================
# BUDGET ENFORCEMENT TESTS
# =============================================================================

class TestCallLimitEnforcement:
    """Test call limit enforcement."""

    @pytest.mark.asyncio
    async def test_call_limit_enforced(self):
        """Test that call limit is enforced."""
        config = ModelConfig(
            slots={"test": ModelSlotConfig(provider="mock", model="test")},
            max_calls_per_episode=3,
        )
        backend = MockBackend()
        router = ModelRouter(config, {"mock": backend})

        req = ModelRequest(
            role=ModelRole.ULTRA_PLANNER,
            messages=[Message(role="user", content="test")],
            trace_id="test-trace",
        )

        # First 3 calls should succeed
        for i in range(3):
            resp, receipt = await router.call("test", req)
            assert resp.text == "mock response"

        # 4th call should fail
        with pytest.raises(ModelCallPolicyError) as exc_info:
            await router.call("test", req)

        assert "call limit exceeded" in str(exc_info.value).lower()
        assert exc_info.value.reason == "call_limit_exceeded"

    @pytest.mark.asyncio
    async def test_different_traces_have_separate_limits(self):
        """Test that different traces have independent call limits."""
        config = ModelConfig(
            slots={"test": ModelSlotConfig(provider="mock", model="test")},
            max_calls_per_episode=2,
        )
        backend = MockBackend()
        router = ModelRouter(config, {"mock": backend})

        # Trace 1: 2 calls
        req1 = ModelRequest(
            role=ModelRole.ULTRA_PLANNER,
            messages=[Message(role="user", content="test")],
            trace_id="trace-1",
        )
        await router.call("test", req1)
        await router.call("test", req1)

        # Trace 2 should still work
        req2 = ModelRequest(
            role=ModelRole.ULTRA_PLANNER,
            messages=[Message(role="user", content="test")],
            trace_id="trace-2",
        )
        resp, _ = await router.call("test", req2)
        assert resp.text == "mock response"


class TestTokenBudgetEnforcement:
    """Test token budget enforcement."""

    @pytest.mark.asyncio
    async def test_token_budget_enforced(self):
        """Test that token budget is enforced."""
        config = ModelConfig(
            slots={"test": ModelSlotConfig(provider="mock", model="test")},
            max_tokens_per_episode=50,  # Each call uses 30 tokens (10 in + 20 out)
            max_calls_per_episode=100,  # High limit so tokens are the constraint
        )
        backend = MockBackend()
        router = ModelRouter(config, {"mock": backend})

        req = ModelRequest(
            role=ModelRole.ULTRA_PLANNER,
            messages=[Message(role="user", content="test")],
            trace_id="test-trace",
        )

        # First call uses 30 tokens, should succeed
        await router.call("test", req)

        # Second call would push to 60 tokens, but pre-check sees 30 < 50, so it runs
        # After second call: 60 tokens used
        await router.call("test", req)

        # Third call: pre-check sees 60 >= 50, should fail
        with pytest.raises(TokenBudgetExceededError) as exc_info:
            await router.call("test", req)

        assert exc_info.value.used == 60
        assert exc_info.value.limit == 50


# =============================================================================
# TIMEOUT ENFORCEMENT TESTS
# =============================================================================

class TestTimeoutEnforcement:
    """Test timeout enforcement."""

    @pytest.mark.asyncio
    async def test_timeout_enforced(self):
        """Test that timeout is enforced."""
        config = ModelConfig(
            slots={"test": ModelSlotConfig(provider="mock", model="test")},
            default_timeout_ms=100,  # 100ms timeout
        )
        backend = MockBackend(delay_ms=500)  # Backend takes 500ms
        router = ModelRouter(config, {"mock": backend})

        req = ModelRequest(
            role=ModelRole.ULTRA_PLANNER,
            messages=[Message(role="user", content="test")],
            trace_id="test-trace",
        )

        with pytest.raises(ModelTimeoutError) as exc_info:
            await router.call("test", req)

        assert exc_info.value.timeout_ms == 100

    @pytest.mark.asyncio
    async def test_slot_specific_timeout(self):
        """Test that slot-specific timeout overrides global default."""
        config = ModelConfig(
            slots={
                "fast": ModelSlotConfig(provider="mock", model="test", max_latency_ms=50),
                "slow": ModelSlotConfig(provider="mock", model="test", max_latency_ms=1000),
            },
            default_timeout_ms=500,
        )
        backend = MockBackend(delay_ms=200)  # 200ms delay
        router = ModelRouter(config, {"mock": backend})

        req = ModelRequest(
            role=ModelRole.ULTRA_PLANNER,
            messages=[Message(role="user", content="test")],
            trace_id="test-trace",
        )

        # Fast slot should timeout (50ms < 200ms)
        with pytest.raises(ModelTimeoutError):
            await router.call("fast", req)

        # Slow slot should succeed (1000ms > 200ms)
        resp, _ = await router.call("slow", req)
        assert resp.text == "mock response"


# =============================================================================
# HIGH-RISK DOMAIN TESTS
# =============================================================================

class TestHighRiskDomainEnforcement:
    """Test high-risk domain restrictions."""

    @pytest.mark.asyncio
    async def test_high_risk_domain_blocked(self):
        """Test that slots not allowed for high-risk domains are blocked."""
        config = ModelConfig(
            slots={
                "safe_slot": ModelSlotConfig(provider="mock", model="test", allow_in_high_risk=False),
                "risk_slot": ModelSlotConfig(provider="mock", model="test", allow_in_high_risk=True),
            },
        )
        backend = MockBackend()
        router = ModelRouter(config, {"mock": backend})

        req = ModelRequest(
            role=ModelRole.ULTRA_PLANNER,
            messages=[Message(role="user", content="test")],
            trace_id="test-trace",
        )

        # Safe slot blocked for chemistry domain
        with pytest.raises(HighRiskDomainError) as exc_info:
            await router.call("safe_slot", req, domain="chemistry")

        assert exc_info.value.domain == "chemistry"

        # Risk slot allowed for chemistry domain
        resp, _ = await router.call("risk_slot", req, domain="chemistry")
        assert resp.text == "mock response"

    @pytest.mark.asyncio
    async def test_non_high_risk_domain_allowed(self):
        """Test that non-high-risk domains are always allowed."""
        config = ModelConfig(
            slots={
                "safe_slot": ModelSlotConfig(provider="mock", model="test", allow_in_high_risk=False),
            },
        )
        backend = MockBackend()
        router = ModelRouter(config, {"mock": backend})

        req = ModelRequest(
            role=ModelRole.ULTRA_PLANNER,
            messages=[Message(role="user", content="test")],
            trace_id="test-trace",
        )

        # Math domain is not high-risk
        resp, _ = await router.call("safe_slot", req, domain="math")
        assert resp.text == "mock response"


# =============================================================================
# TRACE STATS TESTS
# =============================================================================

class TestTraceStats:
    """Test trace statistics tracking."""

    @pytest.mark.asyncio
    async def test_trace_stats_updated(self):
        """Test that trace stats are updated correctly."""
        config = ModelConfig(
            slots={"test": ModelSlotConfig(provider="mock", model="test")},
            max_calls_per_episode=10,
            max_tokens_per_episode=1000,
        )
        backend = MockBackend()
        router = ModelRouter(config, {"mock": backend})

        req = ModelRequest(
            role=ModelRole.ULTRA_PLANNER,
            messages=[Message(role="user", content="test")],
            trace_id="test-trace",
        )

        await router.call("test", req)
        await router.call("test", req)

        stats = router.get_trace_stats("test-trace")

        assert stats["total_calls"] == 2
        assert stats["total_tokens"] == 60  # 2 * (10 + 20)
        assert stats["calls_remaining"] == 8
        assert stats["tokens_remaining"] == 940
        assert "budget_utilization" in stats
        assert stats["budget_utilization"]["calls_pct"] == 20.0

    def test_reset_trace(self):
        """Test that reset_trace clears counters."""
        config = ModelConfig(
            slots={"test": ModelSlotConfig(provider="mock", model="test")},
        )
        router = ModelRouter(config, {})

        # Manually set some values
        router._trace_call_counts["test-trace"] = 5
        router._trace_token_counts["test-trace"] = 100
        router._trace_cost_usd["test-trace"] = 0.5

        router.reset_trace("test-trace")

        assert "test-trace" not in router._trace_call_counts
        assert "test-trace" not in router._trace_token_counts
        assert "test-trace" not in router._trace_cost_usd


# =============================================================================
# STRESS PROFILE TESTS
# =============================================================================

class TestStressProfile:
    """Test stress profile functionality."""

    def test_stress_level_nominal(self):
        """Test nominal stress level."""
        profile = StressProfile(
            token_utilization=0.2,
            call_utilization=0.1,
        )
        assert profile.level == StressLevel.NOMINAL
        assert not profile.degradation_recommended
        assert not profile.shadow_mode_recommended

    def test_stress_level_elevated(self):
        """Test elevated stress level."""
        profile = StressProfile(
            level=StressLevel.ELEVATED,
            token_utilization=0.65,
            call_utilization=0.5,
        )
        assert profile.level == StressLevel.ELEVATED
        assert not profile.degradation_recommended  # 0.65 < 0.8

    def test_stress_level_high(self):
        """Test high stress level with degradation."""
        profile = StressProfile(
            token_utilization=0.85,
            call_utilization=0.7,
        )
        assert profile.degradation_recommended
        assert not profile.shadow_mode_recommended

    def test_stress_level_critical(self):
        """Test critical stress level with shadow mode."""
        profile = StressProfile(
            token_utilization=0.96,
            call_utilization=0.9,
        )
        assert profile.degradation_recommended
        assert profile.shadow_mode_recommended

    def test_from_trace_stats(self):
        """Test creating stress profile from trace stats."""
        stats = {
            "total_calls": 40,
            "total_tokens": 85000,
            "call_limit": 50,
            "token_limit": 100000,
            "calls_remaining": 10,
            "tokens_remaining": 15000,
        }
        profile = StressProfile.from_trace_stats(stats)

        assert profile.call_utilization == 0.8
        assert profile.token_utilization == 0.85
        assert profile.level == StressLevel.HIGH
        assert profile.calls_remaining == 10
        assert profile.tokens_remaining == 15000

    def test_to_dict(self):
        """Test stress profile serialization."""
        profile = StressProfile(
            level=StressLevel.ELEVATED,
            token_utilization=0.5,
            calls_remaining=25,
        )
        d = profile.to_dict()

        assert d["level"] == "elevated"
        assert d["token_utilization"] == 0.5
        assert d["calls_remaining"] == 25


# =============================================================================
# SURVIVAL RECEIPT TESTS
# =============================================================================

class TestSurvivalReceipt:
    """Test survival receipt functionality."""

    def test_survival_receipt_creation(self):
        """Test creating a survival receipt."""
        profile = StressProfile(level=StressLevel.HIGH)
        receipt = SurvivalReceipt(
            mode="math",
            stress_profile=profile,
            outcome=SurvivalOutcome.DEGRADED,
            component="debate_loop",
            action_taken="skipped",
            tokens_used=100,
            features_skipped=["full_debate", "llm_explanation"],
            fallback_used=True,
        )

        assert receipt.receipt_type == "survival"
        assert receipt.outcome == SurvivalOutcome.DEGRADED
        assert receipt.component == "debate_loop"
        assert len(receipt.features_skipped) == 2

    def test_survival_receipt_to_dict(self):
        """Test survival receipt serialization."""
        receipt = SurvivalReceipt(
            mode="math",
            outcome=SurvivalOutcome.TIMEOUT,
            component="llm_validator",
            error_message="Timeout after 60s",
        )
        d = receipt.to_dict()

        assert d["receipt_type"] == "survival"
        assert d["outcome"] == "timeout"
        assert d["component"] == "llm_validator"
        assert d["error_message"] == "Timeout after 60s"


# =============================================================================
# PROMOTION POLICY TESTS
# =============================================================================

class TestPromotionPolicy:
    """Test promotion policy functionality."""

    def test_initial_shadow_mode(self):
        """Test that new components start in shadow mode."""
        policy = PromotionPolicy(component="debate_loop")

        assert policy.mode == "shadow"
        assert not policy.ready_for_promotion
        assert policy.should_use_shadow()

    def test_record_runs(self):
        """Test recording shadow runs."""
        policy = PromotionPolicy(component="debate_loop")

        policy.record_run(success=True, confidence=0.8)
        policy.record_run(success=True, confidence=0.9)
        policy.record_run(success=False, confidence=0.3)

        assert policy.shadow_runs == 3
        assert policy.shadow_successes == 2
        assert policy.shadow_failures == 1
        assert policy.failure_rate == pytest.approx(1/3)
        assert policy.avg_confidence == pytest.approx(2.0/3)

    def test_promotion_criteria_met(self):
        """Test promotion when criteria are met."""
        policy = PromotionPolicy(
            component="debate_loop",
            min_successful_runs=5,
            max_failure_rate=0.2,
            min_confidence_avg=0.7,
        )

        # Record 10 successful runs with high confidence
        for _ in range(10):
            policy.record_run(success=True, confidence=0.85)

        assert policy.ready_for_promotion
        assert policy.failure_rate == 0.0
        assert policy.avg_confidence == pytest.approx(0.85)

    def test_promotion_criteria_not_met_low_runs(self):
        """Test promotion blocked with insufficient runs."""
        policy = PromotionPolicy(
            component="debate_loop",
            min_successful_runs=10,
        )

        for _ in range(5):
            policy.record_run(success=True, confidence=0.9)

        assert not policy.ready_for_promotion

    def test_promotion_criteria_not_met_high_failure(self):
        """Test promotion blocked with high failure rate."""
        policy = PromotionPolicy(
            component="debate_loop",
            min_successful_runs=5,
            max_failure_rate=0.1,
        )

        for _ in range(8):
            policy.record_run(success=True, confidence=0.8)
        for _ in range(2):
            policy.record_run(success=False, confidence=0.2)

        assert not policy.ready_for_promotion
        assert policy.failure_rate == 0.2  # 2/10 = 0.2 > 0.1

    def test_shadow_for_high_risk_domain(self):
        """Test shadow mode enforcement for high-risk domains."""
        policy = PromotionPolicy(
            component="debate_loop",
            mode="production",
            shadow_only_for_high_risk=True,
        )

        # Production mode but high-risk domain should use shadow
        assert policy.should_use_shadow(domain="chemistry")
        assert policy.should_use_shadow(domain="biology")
        assert policy.should_use_shadow(domain="medical")

        # Non-high-risk domain should not use shadow
        assert not policy.should_use_shadow(domain="math")
        assert not policy.should_use_shadow(domain="algebra")

    def test_disabled_mode(self):
        """Test disabled mode never uses shadow."""
        policy = PromotionPolicy(
            component="debate_loop",
            mode="disabled",
        )

        assert not policy.should_use_shadow()
        assert not policy.should_use_shadow(domain="chemistry")

    def test_to_dict(self):
        """Test promotion policy serialization."""
        policy = PromotionPolicy(component="debate_loop")
        policy.record_run(success=True, confidence=0.8)

        d = policy.to_dict()

        assert d["component"] == "debate_loop"
        assert d["mode"] == "shadow"
        assert d["shadow_runs"] == 1
        assert d["failure_rate"] == 0.0
        assert "ready_for_promotion" in d


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestQAHardeningIntegration:
    """Integration tests for QA hardening features."""

    @pytest.mark.asyncio
    async def test_stress_aware_routing(self):
        """Test that routing can be stress-aware."""
        config = ModelConfig(
            slots={"test": ModelSlotConfig(provider="mock", model="test")},
            max_calls_per_episode=10,
            max_tokens_per_episode=1000,
        )
        backend = MockBackend()
        router = ModelRouter(config, {"mock": backend})

        req = ModelRequest(
            role=ModelRole.ULTRA_PLANNER,
            messages=[Message(role="user", content="test")],
            trace_id="test-trace",
        )

        # Make some calls
        for _ in range(8):
            await router.call("test", req)

        # Check stress profile
        stats = router.get_trace_stats("test-trace")
        profile = StressProfile.from_trace_stats(stats)

        assert profile.level == StressLevel.HIGH
        assert profile.degradation_recommended

    @pytest.mark.asyncio
    async def test_survival_receipt_on_budget_exhaustion(self):
        """Test creating survival receipt when budget is exhausted."""
        config = ModelConfig(
            slots={"test": ModelSlotConfig(provider="mock", model="test")},
            max_calls_per_episode=2,
        )
        backend = MockBackend()
        router = ModelRouter(config, {"mock": backend})

        req = ModelRequest(
            role=ModelRole.ULTRA_PLANNER,
            messages=[Message(role="user", content="test")],
            trace_id="test-trace",
        )

        await router.call("test", req)
        await router.call("test", req)

        # Get stats before failure
        stats = router.get_trace_stats("test-trace")
        profile = StressProfile.from_trace_stats(stats)

        try:
            await router.call("test", req)
        except ModelCallPolicyError:
            # Create survival receipt
            receipt = SurvivalReceipt(
                mode="math",
                stress_profile=profile,
                outcome=SurvivalOutcome.BUDGET_EXHAUSTED,
                component="model_router",
                action_taken="blocked",
                calls_used=stats["total_calls"],
                tokens_used=stats["total_tokens"],
            )

            assert receipt.outcome == SurvivalOutcome.BUDGET_EXHAUSTED
            assert receipt.calls_used == 2
