"""
Model Fabric Configuration
===========================

Slots + config: how you declare Opus/GPT-5.1/Gemini without hard-coding.

Key Types:
- ModelSlotConfig: One logical slot → provider + model mapping + defaults
- ModelConfig: Complete model configuration for the organism

Example YAML (model_slots.yaml):

    slots:
      ultra_planner:
        provider: openrouter
        model: anthropic/claude-3.5-opus-2025
        max_tokens: 8192
        temperature: 0.2
      
      math_helper:
        provider: ollama
        model: llama3.1:8b
        temperature: 0.1

On M1 Ultra with no cloud:
- Swap everything to `provider: ollama` or `provider: mlx`
- Keep the same slot names; Ultra Mode doesn't change
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List
from pathlib import Path


@dataclass
class ModelSlotConfig:
    """
    One logical slot → provider + model mapping plus defaults.
    
    Slots are logical names like "ultra_planner", "math_helper".
    This config maps them to concrete provider/model pairs.
    """
    provider: str                 # "openai", "anthropic", "gemini", "ollama", "mlx", "groq", ...
    model: str                    # Provider-specific model name
    max_tokens: int = 4096
    temperature: float = 0.2
    json_mode: bool = False
    top_p: Optional[float] = None
    
    # Resource budgets (for policy enforcement)
    max_latency_ms: Optional[int] = None
    max_cost_usd: Optional[float] = None
    
    # Risk gating
    allow_in_high_risk: bool = True  # Can this slot be used for high-risk world_impact?
    
    # Fallback chain (if this model is unavailable)
    fallback_slots: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "json_mode": self.json_mode,
            "top_p": self.top_p,
            "max_latency_ms": self.max_latency_ms,
            "max_cost_usd": self.max_cost_usd,
            "allow_in_high_risk": self.allow_in_high_risk,
            "fallback_slots": self.fallback_slots,
        }


@dataclass
class ModelConfig:
    """
    Complete model configuration for the organism.
    
    Keys are logical slot names, not provider names.
    This is the single source of truth for model routing.
    """
    slots: Dict[str, ModelSlotConfig] = field(default_factory=dict)
    
    # Global defaults
    default_timeout_ms: int = 60000
    max_calls_per_episode: int = 50
    max_tokens_per_episode: int = 100000
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfig":
        """Parse from dict (e.g., loaded from YAML)."""
        slots = {}
        for slot_name, slot_cfg in data.get("slots", {}).items():
            if isinstance(slot_cfg, dict):
                slots[slot_name] = ModelSlotConfig(**slot_cfg)
            else:
                raise ValueError(f"Invalid slot config for '{slot_name}': {slot_cfg}")
        
        return cls(
            slots=slots,
            default_timeout_ms=data.get("default_timeout_ms", 60000),
            max_calls_per_episode=data.get("max_calls_per_episode", 50),
            max_tokens_per_episode=data.get("max_tokens_per_episode", 100000),
        )
    
    @classmethod
    def from_yaml(cls, path: str) -> "ModelConfig":
        """Load config from YAML file."""
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML required for YAML config. pip install pyyaml")
        
        data = yaml.safe_load(Path(path).read_text())
        return cls.from_dict(data)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "slots": {name: cfg.to_dict() for name, cfg in self.slots.items()},
            "default_timeout_ms": self.default_timeout_ms,
            "max_calls_per_episode": self.max_calls_per_episode,
            "max_tokens_per_episode": self.max_tokens_per_episode,
        }
    
    def get_slot(self, name: str) -> Optional[ModelSlotConfig]:
        """Get slot config by name."""
        return self.slots.get(name)
    
    def list_slots(self) -> List[str]:
        """List all configured slot names."""
        return list(self.slots.keys())


# =============================================================================
# DEFAULT CONFIGS
# =============================================================================

def default_local_config() -> ModelConfig:
    """
    Default config for local-only operation (Ollama).
    
    Use this on M1 Ultra with no cloud access.
    """
    return ModelConfig(
        slots={
            "ultra_planner": ModelSlotConfig(
                provider="ollama",
                model="llama3.1:70b",
                max_tokens=8192,
                temperature=0.2,
            ),
            "builder_synthesizer": ModelSlotConfig(
                provider="ollama",
                model="codestral:latest",
                max_tokens=4096,
                temperature=0.1,
            ),
            "math_helper": ModelSlotConfig(
                provider="ollama",
                model="llama3.1:8b",
                max_tokens=2048,
                temperature=0.1,
            ),
            "guardian_advisor": ModelSlotConfig(
                provider="ollama",
                model="llama3.1:8b",
                max_tokens=1024,
                temperature=0.0,
            ),
            "casual_chat": ModelSlotConfig(
                provider="ollama",
                model="llama3.1:8b",
                max_tokens=2048,
                temperature=0.7,
            ),
        }
    )


def default_echo_config() -> ModelConfig:
    """
    Default config for testing (Echo backend only).
    
    Use this for unit tests - no network, instant responses.
    """
    return ModelConfig(
        slots={
            "ultra_planner": ModelSlotConfig(
                provider="echo",
                model="echo-planner",
                max_tokens=8192,
                temperature=0.2,
            ),
            "builder_synthesizer": ModelSlotConfig(
                provider="echo",
                model="echo-builder",
                max_tokens=4096,
                temperature=0.1,
            ),
            "math_helper": ModelSlotConfig(
                provider="echo",
                model="echo-math",
                max_tokens=2048,
                temperature=0.1,
            ),
            "guardian_advisor": ModelSlotConfig(
                provider="echo",
                model="echo-guardian",
                max_tokens=1024,
                temperature=0.0,
            ),
            "casual_chat": ModelSlotConfig(
                provider="echo",
                model="echo-chat",
                max_tokens=2048,
                temperature=0.7,
            ),
        }
    )


