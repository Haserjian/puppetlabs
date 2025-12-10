"""
Model Fabric Call Policy
=========================

Policy hooks for controlling LLM calls.

The router calls policy.check() before every call.
Policy can:
- Allow the call
- Mutate the request (e.g., lower temperature)
- Deny the call (raise ModelCallPolicyError)

This is where constitutional/Guardian integration happens.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from quintet.model.types import ModelRequest, ModelRole
from quintet.model.config import ModelSlotConfig
from quintet.model.router import ModelCallPolicyError


# =============================================================================
# POLICY PROTOCOL
# =============================================================================

class ModelCallPolicy(ABC):
    """
    Abstract base for call policies.
    
    Implement check() to add custom policy logic.
    """
    
    @abstractmethod
    async def check(
        self,
        slot: str,
        slot_cfg: ModelSlotConfig,
        req: ModelRequest
    ) -> None:
        """
        Check if the call is allowed.
        
        Args:
            slot: Logical slot name
            slot_cfg: Slot configuration
            req: The request (can be mutated)
        
        Raises:
            ModelCallPolicyError: If call should be denied
        """
        pass


# =============================================================================
# COMPOSITE POLICY
# =============================================================================

class CompositePolicy(ModelCallPolicy):
    """
    Combines multiple policies.
    
    All policies must pass (AND semantics).
    """
    
    def __init__(self, policies: List[ModelCallPolicy]):
        self.policies = policies
    
    async def check(
        self,
        slot: str,
        slot_cfg: ModelSlotConfig,
        req: ModelRequest
    ) -> None:
        for policy in self.policies:
            await policy.check(slot, slot_cfg, req)


# =============================================================================
# ROLE ALLOWLIST POLICY
# =============================================================================

class RoleAllowlistPolicy(ModelCallPolicy):
    """
    Only allow certain roles for certain slots.
    
    Example:
        policy = RoleAllowlistPolicy({
            "guardian_advisor": {ModelRole.GUARDIAN_ADVISOR},
            "ultra_planner": {ModelRole.ULTRA_PLANNER, ModelRole.INTERNAL_TOOL},
        })
    """
    
    def __init__(self, slot_roles: Dict[str, Set[ModelRole]]):
        self.slot_roles = slot_roles
    
    async def check(
        self,
        slot: str,
        slot_cfg: ModelSlotConfig,
        req: ModelRequest
    ) -> None:
        if slot in self.slot_roles:
            allowed = self.slot_roles[slot]
            if req.role not in allowed:
                raise ModelCallPolicyError(
                    f"Role {req.role.value} not allowed for slot {slot}",
                    slot=slot,
                    reason="role_not_allowed"
                )


# =============================================================================
# TEMPERATURE CAP POLICY
# =============================================================================

class TemperatureCapPolicy(ModelCallPolicy):
    """
    Cap temperature by role or slot.
    
    Useful for ensuring low-risk outputs for certain roles.
    """
    
    def __init__(
        self,
        role_caps: Optional[Dict[ModelRole, float]] = None,
        slot_caps: Optional[Dict[str, float]] = None,
        default_cap: float = 1.0
    ):
        self.role_caps = role_caps or {}
        self.slot_caps = slot_caps or {}
        self.default_cap = default_cap
    
    async def check(
        self,
        slot: str,
        slot_cfg: ModelSlotConfig,
        req: ModelRequest
    ) -> None:
        # Get the strictest cap
        cap = self.default_cap
        
        if req.role in self.role_caps:
            cap = min(cap, self.role_caps[req.role])
        
        if slot in self.slot_caps:
            cap = min(cap, self.slot_caps[slot])
        
        # Enforce cap (mutate request)
        if req.temperature is not None and req.temperature > cap:
            req.temperature = cap


# =============================================================================
# HIGH RISK WORLD IMPACT POLICY
# =============================================================================

class HighRiskPolicy(ModelCallPolicy):
    """
    Restrict which slots can be used for high-risk world impact.
    
    Uses the slot_cfg.allow_in_high_risk flag and req.metadata.
    """
    
    # World impact categories considered high-risk
    HIGH_RISK_CATEGORIES = {
        "healthcare_medicine",
        "nuclear_radiological",
        "critical_infrastructure",
        "weapons_violence",
        "financial_markets",
    }
    
    async def check(
        self,
        slot: str,
        slot_cfg: ModelSlotConfig,
        req: ModelRequest
    ) -> None:
        world_impact = req.metadata.get("world_impact_category")
        
        if world_impact and world_impact in self.HIGH_RISK_CATEGORIES:
            if not slot_cfg.allow_in_high_risk:
                raise ModelCallPolicyError(
                    f"Slot {slot} not allowed for high-risk category {world_impact}",
                    slot=slot,
                    reason="high_risk_blocked"
                )


# =============================================================================
# BUDGET POLICY
# =============================================================================

@dataclass
class BudgetPolicy(ModelCallPolicy):
    """
    Enforce per-episode token and call budgets.
    
    Note: The router already tracks per-trace counts.
    This policy adds custom per-role or per-slot budgets.
    """
    
    # Per-slot call limits
    slot_call_limits: Dict[str, int] = field(default_factory=dict)
    
    # Per-role call limits
    role_call_limits: Dict[ModelRole, int] = field(default_factory=dict)
    
    # Track calls
    _call_counts: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    async def check(
        self,
        slot: str,
        slot_cfg: ModelSlotConfig,
        req: ModelRequest
    ) -> None:
        trace_id = req.trace_id
        
        # Initialize tracking
        if trace_id not in self._call_counts:
            self._call_counts[trace_id] = {}
        
        counts = self._call_counts[trace_id]
        
        # Check slot limit
        if slot in self.slot_call_limits:
            slot_count = counts.get(f"slot:{slot}", 0)
            if slot_count >= self.slot_call_limits[slot]:
                raise ModelCallPolicyError(
                    f"Slot {slot} call limit exceeded ({slot_count})",
                    slot=slot,
                    reason="slot_limit_exceeded"
                )
            counts[f"slot:{slot}"] = slot_count + 1
        
        # Check role limit
        if req.role in self.role_call_limits:
            role_count = counts.get(f"role:{req.role.value}", 0)
            if role_count >= self.role_call_limits[req.role]:
                raise ModelCallPolicyError(
                    f"Role {req.role.value} call limit exceeded ({role_count})",
                    slot=slot,
                    reason="role_limit_exceeded"
                )
            counts[f"role:{req.role.value}"] = role_count + 1
    
    def reset_trace(self, trace_id: str) -> None:
        """Reset tracking for a trace."""
        self._call_counts.pop(trace_id, None)


# =============================================================================
# DEFAULT POLICIES
# =============================================================================

def default_policy() -> CompositePolicy:
    """
    Create a sensible default policy.
    
    - Cap temperature for guardian_advisor at 0.3
    - Enforce high-risk restrictions
    """
    return CompositePolicy([
        TemperatureCapPolicy(
            role_caps={
                ModelRole.GUARDIAN_ADVISOR: 0.3,
                ModelRole.VERIFICATION: 0.1,
            }
        ),
        HighRiskPolicy(),
    ])


def strict_policy() -> CompositePolicy:
    """
    Create a strict policy for production.
    
    - Temperature caps across the board
    - High-risk restrictions
    - Budget limits
    """
    return CompositePolicy([
        TemperatureCapPolicy(
            role_caps={
                ModelRole.GUARDIAN_ADVISOR: 0.1,
                ModelRole.VERIFICATION: 0.0,
                ModelRole.ULTRA_PLANNER: 0.5,
                ModelRole.BUILDER_SYNTHESIZER: 0.3,
            },
            default_cap=0.7,
        ),
        HighRiskPolicy(),
        BudgetPolicy(
            slot_call_limits={
                "guardian_advisor": 10,
                "verification": 5,
            },
            role_call_limits={
                ModelRole.ULTRA_PLANNER: 20,
                ModelRole.MATH_HELPER: 30,
            },
        ),
    ])


