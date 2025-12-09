"""
Stress Test Decorator
====================

Unit-level stress testing decorator for marking and tracking
functions that should run stress tests.
"""

from functools import wraps
from typing import Callable, List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def stress_test(
    scenario_id: str,
    edge_cases: List[Dict[str, Any]],
    budget_tiers: Optional[List[str]] = None,
    tolerance_sweep: Optional[Dict[str, List[float]]] = None,
    skip_on_ci: bool = False
):
    """Decorator to mark a function for stress testing.

    Args:
        scenario_id: Unique scenario identifier
        edge_cases: List of edge case dictionaries
        budget_tiers: Optional list of budget tiers to test (default: ["standard"])
        tolerance_sweep: Optional tolerance sweep spec
        skip_on_ci: Whether to skip on CI environments

    Returns:
        Decorator function

    Example:
        @stress_test(
            scenario_id="test_solver",
            edge_cases=[
                {"case_id": "overflow", "problem": {"type": "solve", ...}},
                {"case_id": "underflow", "problem": {"type": "solve", ...}}
            ],
            budget_tiers=["light", "standard"]
        )
        def test_my_solver():
            # Test implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        """Decorator implementation."""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Wrapper with stress test tracking."""
            import os
            from quintet.stress.coverage import CoverageTracker

            # Check if should skip on CI
            if skip_on_ci and os.getenv("CI"):
                logger.info(f"Skipping stress test {scenario_id} on CI environment")
                return None

            # Initialize coverage tracker
            tracker = CoverageTracker()

            # Record scenario
            tracker.record_scenario(
                scenario_id=scenario_id,
                name=func.__name__,
                category="unit_stress",
                domain="general"
            )

            # Get effective budget tiers
            tiers = budget_tiers or ["standard"]

            # Store metadata on function for pytest discovery
            results = []

            for tier in tiers:
                for edge_case in edge_cases:
                    try:
                        # Execute test
                        result = func(*args, **kwargs)

                        # Record run
                        tracker.record_run({
                            "run_id": f"{scenario_id}_{edge_case.get('case_id')}_{tier}",
                            "scenario_id": scenario_id,
                            "case_id": edge_case.get("case_id", "unknown"),
                            "passed": result.get("passed", True) if isinstance(result, dict) else True,
                            "confidence": result.get("confidence", 0.8) if isinstance(result, dict) else 0.8,
                            "outcome": result.get("outcome", "success") if isinstance(result, dict) else "success",
                            "budget_used": {"tier": tier},
                        })

                        results.append({
                            "case_id": edge_case.get("case_id"),
                            "tier": tier,
                            "result": result
                        })

                    except Exception as e:
                        logger.error(f"Error in stress test {scenario_id}:{edge_case.get('case_id')}: {e}")

                        tracker.record_run({
                            "run_id": f"{scenario_id}_{edge_case.get('case_id')}_{tier}",
                            "scenario_id": scenario_id,
                            "case_id": edge_case.get("case_id", "unknown"),
                            "passed": False,
                            "confidence": 0.0,
                            "outcome": "failed",
                            "failure_reason": str(e),
                            "budget_used": {"tier": tier},
                        })

            return results

        # Attach metadata for pytest discovery
        wrapper.__stress_test__ = {
            "scenario_id": scenario_id,
            "edge_cases": edge_cases,
            "budget_tiers": budget_tiers or ["standard"],
            "tolerance_sweep": tolerance_sweep,
        }

        return wrapper

    return decorator


def mark_stress_test_coverage(
    scenario_id: str,
    case_id: str,
    priority: int = 3
) -> Callable:
    """Decorator to mark a test as covering a stress scenario.

    Args:
        scenario_id: Scenario being covered
        case_id: Edge case being covered
        priority: Coverage priority (1-5)

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        """Decorator implementation."""

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Execute test with coverage tracking."""
            result = func(*args, **kwargs)

            # Mark coverage in metadata
            if not hasattr(wrapper, "__coverage__"):
                wrapper.__coverage__ = []

            wrapper.__coverage__.append({
                "scenario_id": scenario_id,
                "case_id": case_id,
                "priority": priority
            })

            return result

        wrapper.__mark_coverage__ = {
            "scenario_id": scenario_id,
            "case_id": case_id,
            "priority": priority,
        }

        return wrapper

    return decorator
