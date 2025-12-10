"""
Model Fabric Factory
=====================

Factory functions for building the model router.

Usage:
    # Load from YAML config
    router = build_router_from_config("config/model_slots.yaml")
    
    # Use default local config (Ollama)
    router = build_local_router()
    
    # Use echo config (testing)
    router = build_echo_router()
"""

from typing import Dict, Optional, Any
from pathlib import Path

from quintet.model.config import (
    ModelConfig,
    default_local_config,
    default_echo_config,
)
from quintet.model.router import ModelRouter
from quintet.model.backends import (
    EchoBackend,
    MockBackend,
    OllamaBackend,
    OpenAICompatibleBackend,
    create_echo_backend,
    create_ollama_backend,
    create_openai_backend,
    create_groq_backend,
    create_openrouter_backend,
)
from quintet.model.policy import (
    ModelCallPolicy,
    default_policy,
    strict_policy,
)
from quintet.model.types import ModelBackend


# =============================================================================
# BACKEND REGISTRY
# =============================================================================

def create_backend(
    provider: str,
    config: Optional[Dict[str, Any]] = None
) -> ModelBackend:
    """
    Create a backend by provider name.
    
    Args:
        provider: Provider name (echo, ollama, openai, groq, etc.)
        config: Optional provider-specific config
    
    Returns:
        Backend instance
    """
    config = config or {}
    
    if provider == "echo":
        return EchoBackend()
    
    elif provider == "mock":
        return MockBackend(**config)
    
    elif provider == "ollama":
        return OllamaBackend(
            base_url=config.get("base_url", "http://localhost:11434")
        )
    
    elif provider == "openai":
        return OpenAICompatibleBackend(
            name="openai",
            base_url=config.get("base_url", "https://api.openai.com/v1"),
            api_key=config.get("api_key"),
            api_key_env="OPENAI_API_KEY",
        )
    
    elif provider == "groq":
        return OpenAICompatibleBackend(
            name="groq",
            base_url="https://api.groq.com/openai/v1",
            api_key=config.get("api_key"),
            api_key_env="GROQ_API_KEY",
        )
    
    elif provider == "openrouter":
        return OpenAICompatibleBackend(
            name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key=config.get("api_key"),
            api_key_env="OPENROUTER_API_KEY",
        )
    
    elif provider == "mistral":
        return OpenAICompatibleBackend(
            name="mistral",
            base_url="https://api.mistral.ai/v1",
            api_key=config.get("api_key"),
            api_key_env="MISTRAL_API_KEY",
        )
    
    elif provider == "together":
        return OpenAICompatibleBackend(
            name="together",
            base_url="https://api.together.xyz/v1",
            api_key=config.get("api_key"),
            api_key_env="TOGETHER_API_KEY",
        )
    
    elif provider == "anthropic":
        # Anthropic uses a different API format
        # For now, use OpenRouter as a proxy
        return OpenAICompatibleBackend(
            name="anthropic",
            base_url="https://openrouter.ai/api/v1",
            api_key=config.get("api_key"),
            api_key_env="OPENROUTER_API_KEY",
        )
    
    else:
        raise ValueError(f"Unknown provider: {provider}")


def create_all_backends(
    providers: Optional[set] = None,
    backend_config: Optional[Dict[str, Dict]] = None
) -> Dict[str, ModelBackend]:
    """
    Create backends for multiple providers.
    
    Args:
        providers: Set of provider names (default: echo + ollama)
        backend_config: Per-provider config dicts
    
    Returns:
        Dict of provider_name → backend
    """
    providers = providers or {"echo", "ollama"}
    backend_config = backend_config or {}
    
    backends = {}
    for provider in providers:
        try:
            backends[provider] = create_backend(
                provider,
                backend_config.get(provider)
            )
        except Exception as e:
            # Log but don't fail - some backends may not be configured
            print(f"Warning: Could not create backend '{provider}': {e}")
    
    return backends


# =============================================================================
# ROUTER FACTORIES
# =============================================================================

def build_router(
    config: ModelConfig,
    backends: Optional[Dict[str, ModelBackend]] = None,
    policy: Optional[ModelCallPolicy] = None,
    auto_create_backends: bool = True
) -> ModelRouter:
    """
    Build a router from config.
    
    Args:
        config: Model configuration
        backends: Pre-created backends (optional)
        policy: Call policy (optional)
        auto_create_backends: Auto-create backends for providers in config
    
    Returns:
        Configured ModelRouter
    """
    if backends is None:
        backends = {}
    
    # Auto-create backends for providers in config
    if auto_create_backends:
        providers_needed = {
            slot_cfg.provider
            for slot_cfg in config.slots.values()
        }
        for provider in providers_needed:
            if provider not in backends:
                try:
                    backends[provider] = create_backend(provider)
                except Exception as e:
                    print(f"Warning: Could not create backend '{provider}': {e}")
    
    return ModelRouter(config, backends, policy)


def build_router_from_yaml(
    config_path: str,
    policy: Optional[ModelCallPolicy] = None
) -> ModelRouter:
    """
    Build a router from a YAML config file.
    
    Args:
        config_path: Path to YAML config
        policy: Call policy (optional, uses default if not provided)
    
    Returns:
        Configured ModelRouter
    """
    config = ModelConfig.from_yaml(config_path)
    return build_router(
        config,
        policy=policy or default_policy()
    )


def build_echo_router(
    policy: Optional[ModelCallPolicy] = None
) -> ModelRouter:
    """
    Build a router with echo backend only.
    
    Use for testing - no network calls.
    """
    config = default_echo_config()
    backends = {"echo": EchoBackend()}
    return ModelRouter(config, backends, policy)


def build_local_router(
    base_url: str = "http://localhost:11434",
    policy: Optional[ModelCallPolicy] = None
) -> ModelRouter:
    """
    Build a router with Ollama backend only.
    
    Use for local-first operation on M1 Ultra.
    """
    config = default_local_config()
    backends = {"ollama": OllamaBackend(base_url=base_url)}
    return ModelRouter(config, backends, policy or default_policy())


# =============================================================================
# CONVENIENCE SINGLETON
# =============================================================================

_default_router: Optional[ModelRouter] = None


def get_default_router() -> ModelRouter:
    """
    Get or create the default router.
    
    Uses echo backend by default (safe for testing).
    Call set_default_router() to configure differently.
    """
    global _default_router
    if _default_router is None:
        _default_router = build_echo_router()
    return _default_router


def set_default_router(router: ModelRouter) -> None:
    """Set the default router."""
    global _default_router
    _default_router = router


def reset_default_router() -> None:
    """Reset the default router to None."""
    global _default_router
    _default_router = None


