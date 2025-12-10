"""
Quintet Model Fabric
=====================

Unified LLM abstraction layer for the Quintet organism.

Design Principles:
- Slots, not products: Ultra Mode talks to "ultra_planner", not "claude-3.5-opus"
- Every call is a first-class event with receipts
- Async by default for parallel recursion
- Local-first (Ollama/MLX), cloud-optional (OpenAI/Anthropic/etc.)
- Fully auditable via trace_id/parent_id/call_id

Usage:
    from quintet.model import ModelRouter, ModelRequest, ModelRole, Message
    from quintet.model.factory import build_default_router
    
    router = build_default_router("config/model_slots.yaml")
    
    req = ModelRequest(
        role=ModelRole.ULTRA_PLANNER,
        messages=[
            Message(role="system", content="You are Ultra Mode planner."),
            Message(role="user", content="Create a Python module for auth"),
        ],
        trace_id=episode.episode_id,
    )
    
    response, receipt = await router.call("ultra_planner", req)
"""

from quintet.model.types import (
    ModelRole,
    Message,
    ModelRequest,
    ModelResponse,
    ModelBackend,
)
from quintet.model.config import ModelSlotConfig, ModelConfig
from quintet.model.router import (
    ModelRouter,
    ModelCallReceipt,
    UnknownSlotError,
    UnknownBackendError,
    ModelCallPolicyError,
    ModelTimeoutError,
    TokenBudgetExceededError,
    HighRiskDomainError,
)

__all__ = [
    "ModelRole",
    "Message",
    "ModelRequest",
    "ModelResponse",
    "ModelBackend",
    "ModelSlotConfig",
    "ModelConfig",
    "ModelRouter",
    "ModelCallReceipt",
    # Exceptions
    "UnknownSlotError",
    "UnknownBackendError",
    "ModelCallPolicyError",
    "ModelTimeoutError",
    "TokenBudgetExceededError",
    "HighRiskDomainError",
]


