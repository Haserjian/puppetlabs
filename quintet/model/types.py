"""
Model Fabric Core Types
========================

These are the ONLY types the rest of the system sees for LLM calls.
Ultra Mode, Math Mode, Guardian, etc. never see vendor names - only logical slots.

Key Types:
- Message: Chat message (system/user/assistant/tool)
- ModelRequest: Logical request to an LLM
- ModelResponse: Provider-agnostic response
- ModelBackend: Protocol for backend implementations
- ModelRole: High-level purpose of the call
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Protocol, Literal, Union
from enum import Enum
from uuid import uuid4


# =============================================================================
# MODEL ROLES
# =============================================================================

class ModelRole(str, Enum):
    """
    High-level purpose of the call (for policy + logging).
    
    These are semantic roles, not vendor products.
    Guardian/policy can use these to gate access.
    """
    ULTRA_PLANNER = "ultra_planner"         # Ultra Mode planning
    BUILDER_SYNTHESIZER = "builder_synthesizer"  # Code generation
    GUARDIAN_ADVISOR = "guardian_advisor"   # Safety checks
    MATH_HELPER = "math_helper"             # Math reasoning
    CASUAL_CHAT = "casual_chat"             # General chat
    INTERNAL_TOOL = "internal_tool"         # Self-critique, summarization
    EXPLANATION = "explanation"             # Generating explanations
    VERIFICATION = "verification"           # Verifying outputs


# =============================================================================
# MESSAGES
# =============================================================================

@dataclass
class Message:
    """
    Standardized message unit for chat models.
    
    Modern models (Claude, GPT-4, Gemini) are optimized for chat structures.
    Using List[Message] instead of raw strings allows:
    - Clear system/user/assistant separation
    - Pre-filling assistant responses for JSON steering
    - Proper multi-turn history handling
    """
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None  # Useful for tool outputs or multi-agent IDs
    
    def to_dict(self) -> Dict[str, Any]:
        d = {"role": self.role, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


# =============================================================================
# MODEL REQUEST
# =============================================================================

@dataclass
class ModelRequest:
    """
    Logical request to an LLM, independent of provider.
    
    Ultra Mode / Math Mode build these.
    The router resolves them to concrete models.
    
    Trace Context (crucial for recursion):
    - trace_id: The whole episode's tree of LLM calls (= Episode.episode_id)
    - parent_id: The call_id of whoever spawned this request
    - call_id: Unique for this call (auto-generated)
    
    This gives you a proper tree/DAG when analyzing logs.
    """
    role: ModelRole
    messages: List[Message]
    
    # Recursion / Tracing
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    parent_id: Optional[str] = None
    call_id: str = field(default_factory=lambda: str(uuid4()))
    
    # Behavior knobs (caller can override slot defaults)
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    json_mode: bool = False
    top_p: Optional[float] = None
    stop: Optional[List[str]] = None
    
    # Filled in by router/backends
    target_model: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def for_model(self, model: str) -> "ModelRequest":
        """Return a copy targeting a concrete model."""
        return replace(self, target_model=model)
    
    def child(
        self,
        role: ModelRole,
        messages: List[Message],
        **kwargs
    ) -> "ModelRequest":
        """
        Create a child request with the same trace_id but this call as parent.
        
        Use this for recursive calls within the same episode.
        """
        return ModelRequest(
            role=role,
            messages=messages,
            trace_id=self.trace_id,
            parent_id=self.call_id,
            **kwargs
        )
    
    @classmethod
    def simple(
        cls,
        role: ModelRole,
        system: str,
        prompt: str,
        trace_id: Optional[str] = None,
        **kwargs
    ) -> "ModelRequest":
        """
        Convenience constructor for simple system + user prompt.
        """
        messages = [
            Message(role="system", content=system),
            Message(role="user", content=prompt),
        ]
        return cls(
            role=role,
            messages=messages,
            trace_id=trace_id or str(uuid4()),
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "messages": [m.to_dict() for m in self.messages],
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "call_id": self.call_id,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "json_mode": self.json_mode,
            "top_p": self.top_p,
            "stop": self.stop,
            "target_model": self.target_model,
            "metadata": self.metadata,
        }


# =============================================================================
# MODEL RESPONSE
# =============================================================================

@dataclass
class ModelResponse:
    """
    Provider-agnostic response from an LLM.
    
    Backends fill this in, normalizing across providers.
    """
    text: str
    model_id: str
    provider: str
    tokens_in: int
    tokens_out: int
    finish_reason: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None
    
    # For cost tracking
    cost_estimate_usd: Optional[float] = None
    latency_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "model_id": self.model_id,
            "provider": self.provider,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "finish_reason": self.finish_reason,
            "cost_estimate_usd": self.cost_estimate_usd,
            "latency_ms": self.latency_ms,
        }


# =============================================================================
# MODEL BACKEND PROTOCOL
# =============================================================================

class ModelBackend(Protocol):
    """
    Backend for a specific provider family.
    
    Implementations: EchoBackend, OllamaBackend, OpenAIBackend, etc.
    All backends are async for parallel recursion support.
    """
    
    @property
    def name(self) -> str:
        """Provider name: 'echo', 'ollama', 'openai', 'anthropic', etc."""
        ...
    
    async def complete(self, req: ModelRequest) -> ModelResponse:
        """
        Complete the request asynchronously.
        
        This is async so Ultra Mode can fire multiple calls in parallel.
        """
        ...
    
    def is_available(self) -> bool:
        """Check if this backend is currently available."""
        ...


