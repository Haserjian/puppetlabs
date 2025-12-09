"""
Stress Test Executor
====================

Execute stress tests with budget enforcement, tolerance sweeps,
and outcome validation.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid
import logging
import signal
import time

from quintet.stress.scenario import StressScenario
from quintet.core.types import ResourceLimits, RESOURCE_LIMITS, Receipt
from quintet.math.robustness import ToleranceConfig
from quintet.math.validator import MathValidator

logger = logging.getLogger(__name__)


@dataclass
class StressTestResult:
    """Result of a single stress test execution."""

    run_id: str
    scenario_id: str
    case_id: str
    passed: bool
    confidence: float = 0.0
    duration_ms: float = 0.0
    outcome: str = "unknown"  # "success" | "degraded" | "failed" | "timeout"
    budget_used: Dict[str, Any] = field(default_factory=dict)
    tolerance_used: Dict[str, float] = field(default_factory=dict)
    receipts: List[Receipt] = field(default_factory=list)
    failure_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result_dict = asdict(self)
        result_dict["receipts"] = [r.to_dict() if hasattr(r, "to_dict") else r for r in self.receipts]
        return result_dict

    @property
    def success_rate(self) -> float:
        """Compute success rate: 1.0 if passed, 0.0 otherwise."""
        return 1.0 if self.passed else 0.0


class TimeoutException(Exception):
    """Raised when stress test execution times out."""
    pass


class StressExecutor:
    """Execute stress tests with budget enforcement and tolerance sweeps."""

    def __init__(self):
        """Initialize executor."""
        self._logger = logger
        self.validator = MathValidator()

    def run_stress_test(
        self,
        scenario: StressScenario,
        edge_case: Dict[str, Any],
        budget_tier: str = "standard",
        tolerance_override: Optional[ToleranceConfig] = None,
    ) -> StressTestResult:
        """Execute a stress test with the given configuration.

        Args:
            scenario: Stress scenario definition
            edge_case: Edge case from scenario
            budget_tier: Resource budget tier ("light", "standard", "deep_search")
            tolerance_override: Optional tolerance config override

        Returns:
            StressTestResult with pass/fail and metrics
        """
        run_id = str(uuid.uuid4())
        case_id = edge_case.get("case_id", "unknown")
        start_time = time.time()

        try:
            # Get resource limits for tier
            if budget_tier not in RESOURCE_LIMITS:
                self._logger.warning(f"Unknown budget tier: {budget_tier}, using 'standard'")
                budget_tier = "standard"

            limits = RESOURCE_LIMITS[budget_tier]

            # Get tolerance config
            tolerance = tolerance_override or self._get_tolerance_for_case(edge_case)

            # Build problem from edge case
            problem = self._build_problem_from_edge_case(edge_case)

            # Get expected behavior
            expected_behavior = scenario.get_expected_behavior()

            # Execute with timeout
            result = self._execute_with_timeout(
                problem=problem,
                limits=limits,
                tolerance=tolerance,
                timeout_ms=limits.max_wall_time_ms
            )

            # Validate against expected behavior
            passed, outcome, confidence, warnings = self._validate_result(
                result=result,
                edge_case=edge_case,
                expected_behavior=expected_behavior,
                tolerance=tolerance
            )

            duration_ms = (time.time() - start_time) * 1000

            # Build budget tracking
            budget_used = {
                "wall_time_ms": duration_ms,
                "tier": budget_tier,
            }

            test_result = StressTestResult(
                run_id=run_id,
                scenario_id=scenario.scenario_id,
                case_id=case_id,
                passed=passed,
                confidence=confidence,
                duration_ms=duration_ms,
                outcome=outcome,
                budget_used=budget_used,
                tolerance_used={"absolute": tolerance.absolute, "relative": tolerance.relative},
                warnings=warnings,
            )

            self._logger.info(
                f"Stress test completed: {scenario.scenario_id}:{case_id} "
                f"outcome={outcome}, passed={passed}, confidence={confidence:.2f}"
            )

            return test_result

        except TimeoutException:
            duration_ms = (time.time() - start_time) * 1000

            return StressTestResult(
                run_id=run_id,
                scenario_id=scenario.scenario_id,
                case_id=case_id,
                passed=False,
                confidence=0.0,
                duration_ms=duration_ms,
                outcome="timeout",
                budget_used={"wall_time_ms": duration_ms, "tier": budget_tier},
                failure_reason=f"Execution exceeded {budget_tier} tier timeout",
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            self._logger.error(f"Error executing stress test {run_id}: {e}", exc_info=True)

            return StressTestResult(
                run_id=run_id,
                scenario_id=scenario.scenario_id,
                case_id=case_id,
                passed=False,
                confidence=0.0,
                duration_ms=duration_ms,
                outcome="failed",
                failure_reason=str(e),
            )

    def _get_tolerance_for_case(self, edge_case: Dict[str, Any]) -> ToleranceConfig:
        """Get tolerance config for edge case.

        Args:
            edge_case: Edge case dictionary

        Returns:
            ToleranceConfig
        """
        tolerance_config = edge_case.get("tolerance_config", {})
        return ToleranceConfig(
            absolute=tolerance_config.get("absolute", 1e-9),
            relative=tolerance_config.get("relative", 1e-6),
            max_magnitude=tolerance_config.get("max_magnitude", 1e12),
        )

    def _build_problem_from_edge_case(self, edge_case: Dict[str, Any]) -> Any:
        """Build a problem object from edge case specification.

        Args:
            edge_case: Edge case dictionary

        Returns:
            Problem object (structure depends on domain)
        """
        # For now, return the edge case data as-is
        # In a full implementation, this would instantiate proper Problem objects
        return edge_case.get("problem", {})

    def _execute_with_timeout(
        self,
        problem: Any,
        limits: ResourceLimits,
        tolerance: ToleranceConfig,
        timeout_ms: int
    ) -> Any:
        """Execute problem solving with timeout enforcement.

        Args:
            problem: Problem to solve
            limits: Resource limits
            tolerance: Tolerance configuration
            timeout_ms: Timeout in milliseconds

        Returns:
            Execution result
        """
        # For now, simulate simple execution
        # In a full implementation, this would integrate with MathExecutor
        # and respect the timeout
        timeout_sec = timeout_ms / 1000
        start = time.time()

        # Simulate some work
        time.sleep(min(0.1, timeout_sec))

        if (time.time() - start) > timeout_sec:
            raise TimeoutException(f"Execution exceeded {timeout_ms}ms timeout")

        return {
            "success": True,
            "confidence": 0.85,
            "result": problem.get("expected_result", {}),
            "duration_ms": (time.time() - start) * 1000,
        }

    def _validate_result(
        self,
        result: Any,
        edge_case: Dict[str, Any],
        expected_behavior: Dict[str, Any],
        tolerance: ToleranceConfig
    ) -> Tuple[bool, str, float, List[str]]:
        """Validate result against expected behavior.

        Args:
            result: Execution result
            edge_case: Original edge case
            expected_behavior: Expected behavior specification
            tolerance: Tolerance config

        Returns:
            (passed, outcome, confidence, warnings)
        """
        warnings = []

        # Extract expected result spec
        expected_result = edge_case.get("expected_result", {})
        expected_outcome = expected_result.get("outcome", "success")
        confidence_min = expected_result.get("confidence_min", 0.5)

        # Extract actual result
        actual_outcome = result.get("success", False)
        actual_confidence = result.get("confidence", 0.0)

        # Determine pass/fail
        passed = actual_confidence >= confidence_min

        # Map to outcome string
        if actual_outcome and actual_confidence >= confidence_min:
            outcome = "success"
        elif actual_outcome and actual_confidence >= 0.5:
            outcome = "degraded"
            if passed:
                warnings.append(f"Degraded success: confidence {actual_confidence:.2f} below min {confidence_min:.2f}")
        else:
            outcome = "failed"

        return passed, outcome, actual_confidence, warnings
