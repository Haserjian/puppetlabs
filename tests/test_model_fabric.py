"""
Tests for Model Fabric
=======================

Tests the LLM abstraction layer:
- Types (ModelRequest, ModelResponse, Message)
- Config (ModelSlotConfig, ModelConfig)
- Router (ModelRouter, receipts, parallel calls)
- Backends (EchoBackend, MockBackend)
- Policy (temperature caps, role allowlists)
"""

import pytest
import asyncio
from typing import List

from quintet.model.types import (
    ModelRole, Message, ModelRequest, ModelResponse
)
from quintet.model.config import (
    ModelSlotConfig, ModelConfig,
    default_echo_config, default_local_config
)
from quintet.model.router import (
    ModelRouter, ModelCallReceipt,
    UnknownSlotError, UnknownBackendError
)
from quintet.model.backends import EchoBackend, MockBackend
from quintet.model.policy import (
    TemperatureCapPolicy, RoleAllowlistPolicy,
    HighRiskPolicy, CompositePolicy, BudgetPolicy
)
from quintet.model.factory import (
    build_echo_router, build_router
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def echo_backend():
    return EchoBackend()


@pytest.fixture
def mock_backend():
    return MockBackend()


@pytest.fixture
def echo_config():
    return default_echo_config()


@pytest.fixture
def echo_router(echo_config, echo_backend):
    return ModelRouter(
        config=echo_config,
        backends={"echo": echo_backend}
    )


# =============================================================================
# TYPE TESTS
# =============================================================================

class TestMessage:
    def test_create_message(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name is None
    
    def test_message_with_name(self):
        msg = Message(role="tool", content="Result", name="calculator")
        assert msg.name == "calculator"
    
    def test_message_to_dict(self):
        msg = Message(role="system", content="You are helpful")
        d = msg.to_dict()
        assert d["role"] == "system"
        assert d["content"] == "You are helpful"


class TestModelRequest:
    def test_create_simple_request(self):
        req = ModelRequest.simple(
            role=ModelRole.ULTRA_PLANNER,
            system="You are a planner",
            prompt="Plan this project"
        )
        assert req.role == ModelRole.ULTRA_PLANNER
        assert len(req.messages) == 2
        assert req.messages[0].role == "system"
        assert req.messages[1].role == "user"
    
    def test_request_has_ids(self):
        req = ModelRequest(
            role=ModelRole.MATH_HELPER,
            messages=[Message(role="user", content="2+2")]
        )
        assert req.trace_id  # Auto-generated
        assert req.call_id   # Auto-generated
        assert req.parent_id is None
    
    def test_child_request(self):
        parent = ModelRequest(
            role=ModelRole.ULTRA_PLANNER,
            messages=[Message(role="user", content="Plan")]
        )
        
        child = parent.child(
            role=ModelRole.MATH_HELPER,
            messages=[Message(role="user", content="Calculate")]
        )
        
        # Child shares trace_id but has parent as parent_id
        assert child.trace_id == parent.trace_id
        assert child.parent_id == parent.call_id
        assert child.call_id != parent.call_id
    
    def test_for_model(self):
        req = ModelRequest(
            role=ModelRole.CASUAL_CHAT,
            messages=[Message(role="user", content="Hi")]
        )
        
        targeted = req.for_model("gpt-4o")
        assert targeted.target_model == "gpt-4o"
        assert req.target_model is None  # Original unchanged


# =============================================================================
# CONFIG TESTS
# =============================================================================

class TestModelSlotConfig:
    def test_create_slot_config(self):
        cfg = ModelSlotConfig(
            provider="ollama",
            model="llama3.1:8b",
            max_tokens=2048
        )
        assert cfg.provider == "ollama"
        assert cfg.model == "llama3.1:8b"
        assert cfg.temperature == 0.2  # Default
        assert cfg.allow_in_high_risk is True


class TestModelConfig:
    def test_default_echo_config(self):
        cfg = default_echo_config()
        assert "ultra_planner" in cfg.slots
        assert "math_helper" in cfg.slots
        assert cfg.slots["ultra_planner"].provider == "echo"
    
    def test_from_dict(self):
        data = {
            "slots": {
                "test_slot": {
                    "provider": "mock",
                    "model": "test-model",
                    "max_tokens": 1000,
                }
            }
        }
        cfg = ModelConfig.from_dict(data)
        assert "test_slot" in cfg.slots
        assert cfg.slots["test_slot"].provider == "mock"


# =============================================================================
# BACKEND TESTS
# =============================================================================

class TestEchoBackend:
    @pytest.mark.asyncio
    async def test_echo_response(self, echo_backend):
        req = ModelRequest.simple(
            role=ModelRole.CASUAL_CHAT,
            system="Be helpful",
            prompt="Hello"
        )
        req = req.for_model("echo-test")
        
        resp = await echo_backend.complete(req)
        
        assert resp.provider == "echo"
        assert resp.model_id == "echo-test"
        assert "ECHO BACKEND" in resp.text
        assert resp.tokens_in > 0
    
    @pytest.mark.asyncio
    async def test_echo_json_mode(self, echo_backend):
        req = ModelRequest(
            role=ModelRole.VERIFICATION,
            messages=[Message(role="user", content="Check this")],
            json_mode=True,
            target_model="echo-json"
        )
        
        resp = await echo_backend.complete(req)
        
        import json
        data = json.loads(resp.text)
        assert data["echo"] is True
    
    def test_echo_always_available(self, echo_backend):
        assert echo_backend.is_available() is True


class TestMockBackend:
    @pytest.mark.asyncio
    async def test_mock_default_response(self, mock_backend):
        req = ModelRequest.simple(
            role=ModelRole.CASUAL_CHAT,
            system="",
            prompt="Hello"
        )
        req = req.for_model("mock")
        
        resp = await mock_backend.complete(req)
        assert resp.text == "Mock response"
    
    @pytest.mark.asyncio
    async def test_mock_configured_response(self, mock_backend):
        mock_backend.set_response("math", "42")
        
        req = ModelRequest.simple(
            role=ModelRole.MATH_HELPER,
            system="",
            prompt="What is math?"
        )
        req = req.for_model("mock")
        
        resp = await mock_backend.complete(req)
        assert resp.text == "42"


# =============================================================================
# ROUTER TESTS
# =============================================================================

class TestModelRouter:
    @pytest.mark.asyncio
    async def test_basic_call(self, echo_router):
        req = ModelRequest.simple(
            role=ModelRole.ULTRA_PLANNER,
            system="Plan",
            prompt="Build something"
        )
        
        resp, receipt = await echo_router.call("ultra_planner", req)
        
        assert resp.provider == "echo"
        assert receipt.slot == "ultra_planner"
        assert receipt.role == "ultra_planner"
        assert receipt.prompt_hash  # Non-empty hash
        assert receipt.response_hash
    
    @pytest.mark.asyncio
    async def test_unknown_slot_raises(self, echo_router):
        req = ModelRequest.simple(
            role=ModelRole.CASUAL_CHAT,
            system="",
            prompt="Hello"
        )
        
        with pytest.raises(UnknownSlotError):
            await echo_router.call("nonexistent_slot", req)
    
    @pytest.mark.asyncio
    async def test_receipt_has_trace_context(self, echo_router):
        trace_id = "test-trace-123"
        
        req = ModelRequest.simple(
            role=ModelRole.MATH_HELPER,
            system="Help",
            prompt="Calculate",
            trace_id=trace_id
        )
        
        resp, receipt = await echo_router.call("math_helper", req)
        
        assert receipt.trace_id == trace_id
        assert receipt.call_id == req.call_id
        assert receipt.parent_call_id == req.parent_id
    
    @pytest.mark.asyncio
    async def test_parallel_calls(self, echo_router):
        trace_id = "parallel-test"
        
        calls = [
            ("math_helper", ModelRequest.simple(
                role=ModelRole.MATH_HELPER,
                system="", prompt=f"Problem {i}",
                trace_id=trace_id
            ))
            for i in range(3)
        ]
        
        results = await echo_router.call_parallel(calls)
        
        assert len(results) == 3
        for resp, receipt in results:
            assert receipt.trace_id == trace_id
    
    @pytest.mark.asyncio
    async def test_trace_stats(self, echo_router):
        trace_id = "stats-test"
        
        req = ModelRequest.simple(
            role=ModelRole.CASUAL_CHAT,
            system="", prompt="Hi",
            trace_id=trace_id
        )
        
        await echo_router.call("casual_chat", req)
        await echo_router.call("casual_chat", req)
        
        stats = echo_router.get_trace_stats(trace_id)
        assert stats["total_calls"] == 2
    
    @pytest.mark.asyncio
    async def test_call_limit_enforced(self):
        config = ModelConfig(
            slots={
                "test": ModelSlotConfig(
                    provider="echo", model="test"
                )
            },
            max_calls_per_episode=2
        )
        router = ModelRouter(config, {"echo": EchoBackend()})
        
        trace_id = "limit-test"
        req = ModelRequest.simple(
            role=ModelRole.CASUAL_CHAT,
            system="", prompt="Hi",
            trace_id=trace_id
        )
        
        # First two calls succeed
        await router.call("test", req)
        await router.call("test", req)
        
        # Third call exceeds limit
        from quintet.model.router import ModelCallPolicyError
        with pytest.raises(ModelCallPolicyError):
            await router.call("test", req)


# =============================================================================
# POLICY TESTS
# =============================================================================

class TestTemperatureCapPolicy:
    @pytest.mark.asyncio
    async def test_caps_temperature(self):
        policy = TemperatureCapPolicy(
            role_caps={ModelRole.GUARDIAN_ADVISOR: 0.3}
        )
        
        cfg = ModelSlotConfig(provider="echo", model="test")
        req = ModelRequest.simple(
            role=ModelRole.GUARDIAN_ADVISOR,
            system="", prompt="Check",
            temperature=0.8
        )
        
        await policy.check("test", cfg, req)
        
        assert req.temperature == 0.3  # Capped


class TestRoleAllowlistPolicy:
    @pytest.mark.asyncio
    async def test_blocks_disallowed_role(self):
        policy = RoleAllowlistPolicy({
            "guardian_advisor": {ModelRole.GUARDIAN_ADVISOR}
        })
        
        cfg = ModelSlotConfig(provider="echo", model="test")
        req = ModelRequest.simple(
            role=ModelRole.CASUAL_CHAT,  # Not allowed
            system="", prompt="Hi"
        )
        
        from quintet.model.router import ModelCallPolicyError
        with pytest.raises(ModelCallPolicyError):
            await policy.check("guardian_advisor", cfg, req)


class TestHighRiskPolicy:
    @pytest.mark.asyncio
    async def test_blocks_high_risk_for_disallowed_slot(self):
        policy = HighRiskPolicy()
        
        cfg = ModelSlotConfig(
            provider="echo", model="test",
            allow_in_high_risk=False
        )
        req = ModelRequest.simple(
            role=ModelRole.CASUAL_CHAT,
            system="", prompt="Help"
        )
        req.metadata["world_impact_category"] = "healthcare_medicine"
        
        from quintet.model.router import ModelCallPolicyError
        with pytest.raises(ModelCallPolicyError):
            await policy.check("test", cfg, req)
    
    @pytest.mark.asyncio
    async def test_allows_high_risk_for_allowed_slot(self):
        policy = HighRiskPolicy()
        
        cfg = ModelSlotConfig(
            provider="echo", model="test",
            allow_in_high_risk=True
        )
        req = ModelRequest.simple(
            role=ModelRole.GUARDIAN_ADVISOR,
            system="", prompt="Check safety"
        )
        req.metadata["world_impact_category"] = "healthcare_medicine"
        
        # Should not raise
        await policy.check("test", cfg, req)


# =============================================================================
# FACTORY TESTS
# =============================================================================

class TestFactory:
    def test_build_echo_router(self):
        router = build_echo_router()
        
        assert "echo" in router.backends
        assert "ultra_planner" in router.config.slots
    
    def test_build_router_auto_creates_backends(self):
        config = ModelConfig(
            slots={
                "test": ModelSlotConfig(provider="echo", model="test")
            }
        )
        
        router = build_router(config, auto_create_backends=True)
        
        assert "echo" in router.backends


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    @pytest.mark.asyncio
    async def test_full_recursive_flow(self):
        """Test a full recursive flow with parent-child relationships."""
        router = build_echo_router()
        trace_id = "integration-test"
        receipts = []
        
        # 1. Parent call (Ultra Planner)
        parent_req = ModelRequest.simple(
            role=ModelRole.ULTRA_PLANNER,
            system="Plan the project",
            prompt="Build a calculator",
            trace_id=trace_id
        )
        
        parent_resp, parent_receipt = await router.call("ultra_planner", parent_req)
        receipts.append(parent_receipt)
        
        # 2. Child calls (Math Helper) - in parallel
        child_calls = []
        for i in range(2):
            child_req = parent_req.child(
                role=ModelRole.MATH_HELPER,
                messages=[Message(role="user", content=f"Sub-problem {i}")]
            )
            child_calls.append(("math_helper", child_req))
        
        child_results = await router.call_parallel(child_calls)
        for resp, receipt in child_results:
            receipts.append(receipt)
        
        # Verify trace structure
        assert len(receipts) == 3
        assert all(r.trace_id == trace_id for r in receipts)
        
        # Parent has no parent_call_id
        assert receipts[0].parent_call_id is None
        
        # Children have parent's call_id as their parent
        assert receipts[1].parent_call_id == parent_req.call_id
        assert receipts[2].parent_call_id == parent_req.call_id
        
        # All have unique call_ids
        call_ids = [r.call_id for r in receipts]
        assert len(set(call_ids)) == 3


