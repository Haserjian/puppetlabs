"""
Model Fabric Backends
======================

Backend implementations for different providers.

Current Backends:
- EchoBackend: Test backend (no network, echoes prompts)
- OllamaBackend: Local models via Ollama
- MockBackend: Configurable mock for testing

Future Backends (same interface):
- OpenAIBackend
- AnthropicBackend
- GeminiBackend
- GroqBackend
- MistralBackend
- OpenRouterBackend
- MLXBackend

All backends implement the ModelBackend protocol (async complete()).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Callable
import textwrap
import time
import json

from quintet.model.types import ModelRequest, ModelResponse, Message


# =============================================================================
# ECHO BACKEND (Testing)
# =============================================================================

@dataclass
class EchoBackend:
    """
    Test backend: echoes the prompt with metadata.
    
    Useful for unit tests and offline development.
    No network calls, instant responses.
    """
    name: str = "echo"
    
    async def complete(self, req: ModelRequest) -> ModelResponse:
        """Echo the request as the response."""
        start = time.time()
        
        # Build echo text
        messages_text = "\n".join([
            f"  [{m.role}] {m.content[:100]}{'...' if len(m.content) > 100 else ''}"
            for m in req.messages
        ])
        
        text = textwrap.dedent(f"""
            [ECHO BACKEND]
            role={req.role.value}
            target_model={req.target_model}
            trace_id={req.trace_id}
            call_id={req.call_id}
            parent_id={req.parent_id}
            temperature={req.temperature}
            max_tokens={req.max_tokens}
            json_mode={req.json_mode}
            
            MESSAGES:
            {messages_text}
        """).strip()
        
        # If JSON mode, return valid JSON
        if req.json_mode:
            text = json.dumps({
                "echo": True,
                "role": req.role.value,
                "model": req.target_model,
                "message_count": len(req.messages),
            })
        
        latency = (time.time() - start) * 1000
        
        return ModelResponse(
            text=text,
            model_id=req.target_model or "echo-model",
            provider=self.name,
            tokens_in=sum(len(m.content.split()) for m in req.messages),
            tokens_out=len(text.split()),
            finish_reason="echo",
            raw=None,
            latency_ms=latency,
        )
    
    def is_available(self) -> bool:
        """Echo backend is always available."""
        return True


# =============================================================================
# MOCK BACKEND (Configurable Testing)
# =============================================================================

@dataclass
class MockBackend:
    """
    Configurable mock backend for testing specific scenarios.
    
    You can set up expected responses for different prompts/roles.
    """
    name: str = "mock"
    
    # Map of (role, prompt_contains) → response
    responses: Dict[str, str] = field(default_factory=dict)
    default_response: str = "Mock response"
    
    # Simulate latency
    latency_ms: float = 10.0
    
    # Simulate failures
    should_fail: bool = False
    fail_message: str = "Mock failure"
    
    async def complete(self, req: ModelRequest) -> ModelResponse:
        """Return configured mock response."""
        import asyncio
        
        # Simulate latency
        await asyncio.sleep(self.latency_ms / 1000)
        
        if self.should_fail:
            raise RuntimeError(self.fail_message)
        
        # Find matching response
        text = self.default_response
        for key, response in self.responses.items():
            if key in req.role.value or any(key in m.content for m in req.messages):
                text = response
                break
        
        return ModelResponse(
            text=text,
            model_id=req.target_model or "mock-model",
            provider=self.name,
            tokens_in=sum(len(m.content.split()) for m in req.messages),
            tokens_out=len(text.split()),
            finish_reason="mock",
            raw=None,
            latency_ms=self.latency_ms,
        )
    
    def is_available(self) -> bool:
        return True
    
    def set_response(self, key: str, response: str) -> None:
        """Set a response for a key (matches role or prompt content)."""
        self.responses[key] = response


# =============================================================================
# OLLAMA BACKEND (Local Models)
# =============================================================================

@dataclass
class OllamaBackend:
    """
    Local-only backend for Ollama.
    
    Requires Ollama running at base_url (default: http://localhost:11434).
    Uses the /api/chat endpoint for message-based completion.
    """
    name: str = "ollama"
    base_url: str = "http://localhost:11434"
    timeout: float = 600.0  # 10 minutes for large models
    
    async def complete(self, req: ModelRequest) -> ModelResponse:
        """Complete via Ollama's chat API."""
        try:
            import aiohttp
        except ImportError:
            raise ImportError("aiohttp required for OllamaBackend. pip install aiohttp")
        
        if not req.target_model:
            raise ValueError("OllamaBackend requires req.target_model to be set")
        
        start = time.time()
        
        # Convert messages to Ollama format
        ollama_messages = [
            {"role": m.role, "content": m.content}
            for m in req.messages
        ]
        
        payload: Dict[str, Any] = {
            "model": req.target_model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": req.temperature or 0.2,
                "num_predict": req.max_tokens or 4096,
            },
        }
        
        # JSON mode
        if req.json_mode:
            payload["format"] = "json"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        
        latency = (time.time() - start) * 1000
        
        # Extract response
        text = data.get("message", {}).get("content", "")
        
        return ModelResponse(
            text=text,
            model_id=req.target_model,
            provider=self.name,
            tokens_in=data.get("prompt_eval_count", 0),
            tokens_out=data.get("eval_count", 0),
            finish_reason=data.get("done_reason", "stop"),
            raw=data,
            latency_ms=latency,
        )
    
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            import urllib.request
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=2) as resp:
                return resp.status == 200
        except:
            return False


# =============================================================================
# OPENAI-COMPATIBLE BACKEND (OpenAI, Groq, OpenRouter, etc.)
# =============================================================================

@dataclass
class OpenAICompatibleBackend:
    """
    Backend for OpenAI-compatible APIs.
    
    Works with:
    - OpenAI (api.openai.com)
    - Groq (api.groq.com)
    - OpenRouter (openrouter.ai)
    - Together AI
    - Anyscale
    - vLLM
    - etc.
    
    Requires API key in environment or passed directly.
    """
    name: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    api_key: Optional[str] = None
    api_key_env: str = "OPENAI_API_KEY"
    timeout: float = 120.0
    
    def _get_api_key(self) -> str:
        """Get API key from config or environment."""
        if self.api_key:
            return self.api_key
        
        import os
        key = os.environ.get(self.api_key_env)
        if not key:
            raise ValueError(
                f"API key required. Set {self.api_key_env} or pass api_key."
            )
        return key
    
    async def complete(self, req: ModelRequest) -> ModelResponse:
        """Complete via OpenAI-compatible chat API."""
        try:
            import aiohttp
        except ImportError:
            raise ImportError("aiohttp required. pip install aiohttp")
        
        if not req.target_model:
            raise ValueError("target_model required")
        
        start = time.time()
        api_key = self._get_api_key()
        
        # Build messages
        messages = [m.to_dict() for m in req.messages]
        
        payload: Dict[str, Any] = {
            "model": req.target_model,
            "messages": messages,
            "temperature": req.temperature or 0.2,
            "max_tokens": req.max_tokens or 4096,
        }
        
        if req.top_p is not None:
            payload["top_p"] = req.top_p
        
        if req.stop:
            payload["stop"] = req.stop
        
        if req.json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        
        latency = (time.time() - start) * 1000
        
        # Extract response
        choice = data.get("choices", [{}])[0]
        text = choice.get("message", {}).get("content", "")
        finish_reason = choice.get("finish_reason")
        
        usage = data.get("usage", {})
        
        return ModelResponse(
            text=text,
            model_id=req.target_model,
            provider=self.name,
            tokens_in=usage.get("prompt_tokens", 0),
            tokens_out=usage.get("completion_tokens", 0),
            finish_reason=finish_reason,
            raw=data,
            latency_ms=latency,
        )
    
    def is_available(self) -> bool:
        """Check if API key is available."""
        try:
            self._get_api_key()
            return True
        except ValueError:
            return False


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_echo_backend() -> EchoBackend:
    """Create an echo backend for testing."""
    return EchoBackend()


def create_ollama_backend(base_url: str = "http://localhost:11434") -> OllamaBackend:
    """Create an Ollama backend."""
    return OllamaBackend(base_url=base_url)


def create_openai_backend(
    api_key: Optional[str] = None,
    base_url: str = "https://api.openai.com/v1"
) -> OpenAICompatibleBackend:
    """Create an OpenAI backend."""
    return OpenAICompatibleBackend(
        name="openai",
        base_url=base_url,
        api_key=api_key,
        api_key_env="OPENAI_API_KEY",
    )


def create_groq_backend(api_key: Optional[str] = None) -> OpenAICompatibleBackend:
    """Create a Groq backend."""
    return OpenAICompatibleBackend(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
        api_key_env="GROQ_API_KEY",
    )


def create_openrouter_backend(api_key: Optional[str] = None) -> OpenAICompatibleBackend:
    """Create an OpenRouter backend."""
    return OpenAICompatibleBackend(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        api_key_env="OPENROUTER_API_KEY",
    )


