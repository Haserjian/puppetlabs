"""
Ultra Mode Router
=================

Single arbitration point between Build Mode and Math Mode.

For now this is a minimal implementation that keeps the public
contract stable for tests and higher‑level callers:

- `UltraModeRouter` exposes a `route(query, synthesis=None)` method
  that returns a `(mode_name, intent)` tuple.
- `RouterDecision` is a small dataclass wrapper that some callers
  may use instead of the raw tuple.

The internal routing logic can be made more sophisticated over time
without changing this interface.
"""

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from quintet.core.types import Mode


@dataclass
class RouterDecision:
    """Result of routing a query to a mode."""
    mode: str                       # "math" | "build" | "default"
    intent: Optional[Any] = None    # Mode‑specific intent object


class UltraModeRouter:
    """
    Minimal router wiring Build Mode and Math Mode.

    This implementation delegates detection to the two modes'
    `detect()` methods and chooses a mode using simple confidence
    thresholds. It is intentionally conservative and can be replaced
    with the richer arbitration logic described in the spec without
    changing the external API.
    """

    def __init__(self, build_mode: Mode, math_mode: Mode):
        self.build_mode = build_mode
        self.math_mode = math_mode

        # Simple thresholds; can be tuned or made dynamic later.
        self.MATH_THRESHOLD = 0.6
        self.BUILD_THRESHOLD = 0.5

    def route(self, query: str, synthesis: Optional[dict] = None) -> Tuple[str, Any]:
        """
        Decide which mode should handle the query.

        Returns:
            (mode_name, intent)
            mode_name is "math", "build", or "default".
            intent is the mode‑specific intent object (or None).
        """
        math_intent = self.math_mode.detect(query, synthesis)
        build_intent = self.build_mode.detect(query, synthesis)

        # Extract confidences in a mode‑specific way
        math_conf = getattr(math_intent, "confidence", 0.0) if getattr(math_intent, "is_math", False) else 0.0
        build_conf = getattr(build_intent, "confidence", 0.0) if getattr(build_intent, "is_build", False) or getattr(build_intent, "is_buildable", False) else 0.0

        # Neither passes threshold → default
        if math_conf < self.MATH_THRESHOLD and build_conf < self.BUILD_THRESHOLD:
            return "default", None

        # Clear winner
        if math_conf >= self.MATH_THRESHOLD and math_conf > build_conf:
            return "math", math_intent
        if build_conf >= self.BUILD_THRESHOLD and build_conf > math_conf:
            return "build", build_intent

        # Tie‑break: prefer build for ambiguous "create/make/build" verbs
        query_lower = query.lower()
        build_verbs = ["create", "make", "build", "generate", "implement", "write"]
        if any(v in query_lower for v in build_verbs):
            return "build", build_intent

        # Otherwise, default to math when both are plausible
        return "math", math_intent

