"""
Model Fabric Router
====================

Central gateway for ALL LLM calls.

Ultra Mode / Math Mode / Guardian talk to this via slot names.
The router:
1. Resolves slot → provider + model
2. Merges config defaults with request
3. Calls the appropriate backend (async)
4. Creates a receipt for every call

Key Types:
- ModelRouter: The central gateway
- ModelCallReceipt: Receipt for each LLM call (links to Episode via trace_id)
"""

from __future__ import annotations

import hashlib
import asyncio
import time
from dataclasses import dataclass, field, replace
from typing import Dict, Optional, Tuple, List, Any, TYPE_CHECKING, ClassVar
from datetime import datetime

from quintet.model.types import (
    ModelRequest, ModelResponse, ModelBackend, Message
)
from quintet.model.config import ModelConfig, ModelSlotConfig
from quintet.core.types import Receipt

if TYPE_CHECKING:
    from quintet.model.policy import ModelCallPolicy


# =============================================================================
# MODEL CALL RECEIPT
# =============================================================================

@dataclass
class ModelCallReceipt(Receipt):
    """
    Receipt specifically for LLM calls.
    
    Links to Episode via trace_id (= Episode.episode_id).
    Forms a tree via parent_call_id → call_id.
    """
    receipt_type: str = "model_call"
    
    # Provider info
    provider: str = "unknown"
    model_id: str = "unknown"
    slot: Optional[str] = None
    role: Optional[str] = None
    
    # Token usage
    tokens_in: int = 0
    tokens_out: int = 0
    
    # Request params
    temperature: Optional[float] = None
    json_mode: bool = False
    
    # Hashes for audit (prompt/response not stored, just hashes)
    prompt_hash: str = ""
    response_hash: str = ""
    
    # Recursion context (crucial for tracing)
    trace_id: str = ""
    parent_call_id: Optional[str] = None
    call_id: str = ""
    
    # Performance
    latency_ms: Optional[float] = None
    cost_estimate_usd: Optional[float] = None
    
    # Subsystem identification
    subsystem: str = "model_fabric"
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "provider": self.provider,
            "model_id": self.model_id,
            "slot": self.slot,
            "role": self.role,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "temperature": self.temperature,
            "json_mode": self.json_mode,
            "prompt_hash": self.prompt_hash,
            "response_hash": self.response_hash,
            "trace_id": self.trace_id,
            "parent_call_id": self.parent_call_id,
            "call_id": self.call_id,
            "latency_ms": self.latency_ms,
            "cost_estimate_usd": self.cost_estimate_usd,
            "subsystem": self.subsystem,
        })
        return base


# =============================================================================
# EXCEPTIONS
# =============================================================================

class UnknownSlotError(Exception):
    """Raised when a slot is not configured."""
    pass


class UnknownBackendError(Exception):
    """Raised when no backend is registered for a provider."""
    pass


class ModelCallPolicyError(Exception):
    """Raised when a call is denied by policy."""
    def __init__(self, message: str, slot: str, reason: str):
        super().__init__(message)
        self.slot = slot
        self.reason = reason


class ModelTimeoutError(Exception):
    """Raised when a model call times out."""
    def __init__(self, message: str, slot: str, timeout_ms: int):
        super().__init__(message)
        self.slot = slot
        self.timeout_ms = timeout_ms


class TokenBudgetExceededError(Exception):
    """Raised when token budget for an episode is exceeded."""
    def __init__(self, message: str, trace_id: str, used: int, limit: int):
        super().__init__(message)
        self.trace_id = trace_id
        self.used = used
        self.limit = limit


class HighRiskDomainError(Exception):
    """Raised when a slot is used in a high-risk context but not allowed."""
    def __init__(self, message: str, slot: str, domain: str):
        super().__init__(message)
        self.slot = slot
        self.domain = domain


# =============================================================================
# MODEL ROUTER
# =============================================================================

class ModelRouter:
    """
    Central gateway for all LLM calls.
    
    Ultra Mode / Math Mode / Guardian talk to this via slot names.
    Never knows about specific prompts - just routes and receipts.
    
    Usage:
        router = ModelRouter(config, backends)
        
        req = ModelRequest(
            role=ModelRole.ULTRA_PLANNER,
            messages=[...],
            trace_id=episode_id,
        )
        
        response, receipt = await router.call("ultra_planner", req)
        episode.receipts.append(receipt)
    """
    
    # Domains considered high-risk by default (require allow_in_high_risk=True)
    HIGH_RISK_DOMAINS: List[str] = [
        "chemistry",
        "biology",
        "weapons",
        "malware",
        "financial",
        "medical",
    ]

    def __init__(
        self,
        config: ModelConfig,
        backends: Dict[str, ModelBackend],
        policy: Optional["ModelCallPolicy"] = None
    ):
        self.config = config
        self.backends = backends  # provider_name → backend
        self.policy = policy

        # Per-trace counters (for budget enforcement)
        self._trace_call_counts: Dict[str, int] = {}
        self._trace_token_counts: Dict[str, int] = {}

        # Per-trace cost tracking
        self._trace_cost_usd: Dict[str, float] = {}
    
    def _hash(self, text: str) -> str:
        """SHA-256 hash for audit trails."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
    
    def _flatten_messages(self, messages: List[Message]) -> str:
        """Flatten messages to string for hashing."""
        return "\n".join([f"[{m.role}] {m.content}" for m in messages])
    
    async def call(
        self,
        slot: str,
        req: ModelRequest,
        mode: str = "unknown",
        domain: Optional[str] = None,
    ) -> Tuple[ModelResponse, ModelCallReceipt]:
        """
        Route a model request through the appropriate backend.

        Args:
            slot: Logical slot name (e.g., "ultra_planner")
            req: The model request
            mode: Calling mode for receipt ("build", "math", etc.)
            domain: Optional domain for high-risk checks

        Returns:
            (ModelResponse, ModelCallReceipt)

        Raises:
            UnknownSlotError: If slot is not configured
            UnknownBackendError: If no backend for provider
            ModelCallPolicyError: If policy denies the call
            ModelTimeoutError: If the call times out
            TokenBudgetExceededError: If token budget exceeded
            HighRiskDomainError: If slot not allowed for high-risk domain
        """
        start_time = time.time()

        # 1. Resolve slot
        slot_cfg = self.config.slots.get(slot)
        if not slot_cfg:
            raise UnknownSlotError(f"No model slot configured for '{slot}'")

        # 2. Resolve backend
        backend = self.backends.get(slot_cfg.provider)
        if not backend:
            raise UnknownBackendError(
                f"No backend registered for provider '{slot_cfg.provider}'"
            )

        # 3. Check high-risk domain restrictions
        if domain and domain.lower() in self.HIGH_RISK_DOMAINS:
            if not slot_cfg.allow_in_high_risk:
                raise HighRiskDomainError(
                    f"Slot '{slot}' is not allowed for high-risk domain '{domain}'",
                    slot=slot,
                    domain=domain
                )

        # 4. Merge config defaults with request
        effective_req = replace(
            req,
            target_model=slot_cfg.model,
            temperature=req.temperature if req.temperature is not None else slot_cfg.temperature,
            max_tokens=req.max_tokens or slot_cfg.max_tokens,
            json_mode=req.json_mode or slot_cfg.json_mode,
            top_p=req.top_p if req.top_p is not None else slot_cfg.top_p,
        )

        # 5. Check policy (if configured)
        if self.policy:
            await self.policy.check(slot, slot_cfg, effective_req)

        # 6. Check per-episode call budget
        trace_calls = self._trace_call_counts.get(effective_req.trace_id, 0)
        if trace_calls >= self.config.max_calls_per_episode:
            raise ModelCallPolicyError(
                f"Episode call limit exceeded ({trace_calls} >= {self.config.max_calls_per_episode})",
                slot=slot,
                reason="call_limit_exceeded"
            )

        # 7. Check per-episode token budget (pre-check based on current usage)
        trace_tokens = self._trace_token_counts.get(effective_req.trace_id, 0)
        if trace_tokens >= self.config.max_tokens_per_episode:
            raise TokenBudgetExceededError(
                f"Episode token budget exceeded ({trace_tokens} >= {self.config.max_tokens_per_episode})",
                trace_id=effective_req.trace_id,
                used=trace_tokens,
                limit=self.config.max_tokens_per_episode
            )

        # 8. Determine timeout (slot-specific or global default)
        timeout_ms = slot_cfg.max_latency_ms or self.config.default_timeout_ms
        timeout_sec = timeout_ms / 1000.0

        # 9. Call backend with timeout
        try:
            resp = await asyncio.wait_for(
                backend.complete(effective_req),
                timeout=timeout_sec
            )
        except asyncio.TimeoutError:
            raise ModelTimeoutError(
                f"Model call to slot '{slot}' timed out after {timeout_ms}ms",
                slot=slot,
                timeout_ms=timeout_ms
            )

        # 10. Update counters
        self._trace_call_counts[effective_req.trace_id] = trace_calls + 1
        new_token_count = trace_tokens + resp.tokens_in + resp.tokens_out
        self._trace_token_counts[effective_req.trace_id] = new_token_count

        # 11. Update cost tracking
        if resp.cost_estimate_usd:
            self._trace_cost_usd[effective_req.trace_id] = (
                self._trace_cost_usd.get(effective_req.trace_id, 0.0) +
                resp.cost_estimate_usd
            )

        # 12. Post-check token budget (warn if exceeded after this call)
        if new_token_count > self.config.max_tokens_per_episode:
            # Don't raise here - the call succeeded, but log/flag for next call
            pass

        # 13. Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # 14. Check per-slot latency limit (warning only, call already completed)
        latency_exceeded = False
        if slot_cfg.max_latency_ms and latency_ms > slot_cfg.max_latency_ms:
            latency_exceeded = True

        # 15. Check per-slot cost limit
        cost_exceeded = False
        if slot_cfg.max_cost_usd and resp.cost_estimate_usd:
            if resp.cost_estimate_usd > slot_cfg.max_cost_usd:
                cost_exceeded = True

        # 16. Build receipt
        full_prompt_text = self._flatten_messages(effective_req.messages)

        receipt = ModelCallReceipt(
            mode=mode,
            result_id=None,
            timestamp=datetime.utcnow().isoformat(),
            provider=resp.provider,
            model_id=resp.model_id,
            slot=slot,
            role=effective_req.role.value,
            tokens_in=resp.tokens_in,
            tokens_out=resp.tokens_out,
            temperature=effective_req.temperature,
            json_mode=effective_req.json_mode,
            prompt_hash=self._hash(full_prompt_text),
            response_hash=self._hash(resp.text),
            trace_id=effective_req.trace_id,
            parent_call_id=effective_req.parent_id,
            call_id=effective_req.call_id,
            latency_ms=latency_ms,
            cost_estimate_usd=resp.cost_estimate_usd,
        )

        # Add warning flags to receipt metadata (via notes field if needed)
        if latency_exceeded or cost_exceeded:
            receipt.subsystem = f"{receipt.subsystem}{'|latency_exceeded' if latency_exceeded else ''}{'|cost_exceeded' if cost_exceeded else ''}"

        return resp, receipt
    
    async def call_parallel(
        self,
        calls: List[Tuple[str, ModelRequest]],
        mode: str = "unknown"
    ) -> List[Tuple[ModelResponse, ModelCallReceipt]]:
        """
        Execute multiple calls in parallel.
        
        Use this for parallel subproblem solving.
        
        Args:
            calls: List of (slot, request) tuples
            mode: Calling mode for receipts
        
        Returns:
            List of (response, receipt) tuples in same order as input
        """
        tasks = [
            self.call(slot, req, mode)
            for slot, req in calls
        ]
        return await asyncio.gather(*tasks)
    
    def get_trace_stats(self, trace_id: str) -> Dict[str, Any]:
        """Get statistics for a trace (episode)."""
        total_calls = self._trace_call_counts.get(trace_id, 0)
        total_tokens = self._trace_token_counts.get(trace_id, 0)
        total_cost = self._trace_cost_usd.get(trace_id, 0.0)

        return {
            "trace_id": trace_id,
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "call_limit": self.config.max_calls_per_episode,
            "token_limit": self.config.max_tokens_per_episode,
            "calls_remaining": max(0, self.config.max_calls_per_episode - total_calls),
            "tokens_remaining": max(0, self.config.max_tokens_per_episode - total_tokens),
            "budget_utilization": {
                "calls_pct": (total_calls / self.config.max_calls_per_episode * 100) if self.config.max_calls_per_episode > 0 else 0,
                "tokens_pct": (total_tokens / self.config.max_tokens_per_episode * 100) if self.config.max_tokens_per_episode > 0 else 0,
            }
        }

    def reset_trace(self, trace_id: str) -> None:
        """Reset counters for a trace (call after episode completes)."""
        self._trace_call_counts.pop(trace_id, None)
        self._trace_token_counts.pop(trace_id, None)
        self._trace_cost_usd.pop(trace_id, None)
    
    def list_slots(self) -> List[str]:
        """List all configured slots."""
        return list(self.config.slots.keys())
    
    def list_backends(self) -> List[str]:
        """List all registered backends."""
        return list(self.backends.keys())


