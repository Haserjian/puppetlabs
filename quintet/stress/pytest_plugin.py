"""
Pytest Plugin for Stress Testing
================================

Pytest plugin for automatic discovery and execution of stress scenarios
from YAML files.
"""

import pytest
from pathlib import Path
from typing import Generator, List, Optional, Any
import logging

from quintet.stress.scenario import StressScenario
from quintet.stress.executor import StressExecutor, StressTestResult
from quintet.stress.coverage import CoverageTracker

logger = logging.getLogger(__name__)


def pytest_addoption(parser: Any) -> None:
    """Add pytest command-line options."""
    parser.addoption(
        "--stress-scenarios",
        default="tests/stress/scenarios",
        help="Directory containing stress scenario YAML files"
    )
    parser.addoption(
        "--stress-coverage-report",
        action="store_true",
        help="Generate coverage report after stress tests"
    )
    parser.addoption(
        "--stress-tier",
        default="standard",
        choices=["light", "standard", "deep_search"],
        help="Resource budget tier for stress tests"
    )
    parser.addoption(
        "--stress-skip-slow",
        action="store_true",
        help="Skip slow stress tests"
    )


def pytest_configure(config: Any) -> None:
    """Configure pytest for stress testing."""
    config.addinivalue_line(
        "markers",
        "stress: mark test as a stress test"
    )


def pytest_collect_file(
    parent: Any,
    file_path: Path
) -> Optional["StressScenarioFile"]:
    """Collect stress scenario YAML files.

    Args:
        parent: Parent collector
        file_path: File path being collected

    Returns:
        StressScenarioFile if file is a stress scenario, None otherwise
    """
    # Only collect YAML files in stress/scenarios directories
    if file_path.suffix == ".yaml":
        # Check if it's in a scenarios directory
        if "stress/scenarios" in str(file_path) or "stress/scenario" in str(file_path):
            return StressScenarioFile.from_parent(parent, path=file_path)

    return None


class StressScenarioFile(pytest.File):
    """Pytest File item for stress scenario YAML files."""

    def collect(self) -> Generator["StressScenarioTest", None, None]:
        """Collect test items from scenario file.

        Yields:
            StressScenarioTest items for each edge case
        """
        try:
            # Load scenario from YAML
            scenario = StressScenario.from_yaml(str(self.path))

            # Create a test item for each edge case
            for edge_case in scenario.edge_cases:
                case_id = edge_case.get("case_id", "unknown")
                test_name = f"{scenario.scenario_id}::{case_id}"

                yield StressScenarioTest.from_parent(
                    self,
                    name=test_name,
                    scenario=scenario,
                    edge_case=edge_case
                )

        except Exception as e:
            logger.error(f"Error loading stress scenario from {self.path}: {e}")
            # Yield a failed test item
            yield StressScenarioTest.from_parent(
                self,
                name=f"error_loading_{self.path.stem}",
                scenario=None,
                edge_case={"case_id": "error"},
                error=str(e)
            )


class StressScenarioTest(pytest.Item):
    """Pytest Item for a single stress scenario test."""

    def __init__(
        self,
        *,
        name: str,
        parent: Any,
        scenario: Optional[StressScenario] = None,
        edge_case: Optional[dict] = None,
        error: Optional[str] = None
    ) -> None:
        """Initialize stress test item.

        Args:
            name: Test name
            parent: Parent collector
            scenario: StressScenario instance
            edge_case: Edge case dictionary
            error: Error message if scenario failed to load
        """
        super().__init__(name, parent)
        self.scenario = scenario
        self.edge_case = edge_case
        self.error = error
        self.add_marker("stress")

    def runtest(self) -> None:
        """Execute the stress test.

        Raises:
            Exception: If test fails
        """
        if self.error:
            raise Exception(f"Failed to load scenario: {self.error}")

        if not self.scenario or not self.edge_case:
            raise Exception("Invalid scenario or edge case")

        # Get pytest configuration
        config = self.config
        budget_tier = config.getoption("--stress-tier")
        skip_slow = config.getoption("--stress-skip-slow")

        # Skip if requested
        if skip_slow and self.scenario.category != "edge_cases":
            pytest.skip(f"Skipping slow stress test: {self.scenario.scenario_id}")

        # Execute stress test
        executor = StressExecutor()
        result = executor.run_stress_test(
            scenario=self.scenario,
            edge_case=self.edge_case,
            budget_tier=budget_tier
        )

        # Record to coverage tracker
        tracker = CoverageTracker()
        tracker.record_scenario(
            scenario_id=self.scenario.scenario_id,
            name=self.scenario.name,
            category=self.scenario.category,
            domain=self.scenario.domain
        )
        tracker.record_run(result.to_dict())

        # Assert test passed
        assert result.passed, (
            f"Stress test failed: {result.outcome}\n"
            f"Confidence: {result.confidence:.2f}\n"
            f"Duration: {result.duration_ms:.1f}ms\n"
            f"Reason: {result.failure_reason or 'No reason provided'}"
        )

    def repr_failure(self, excinfo: Any) -> List[str]:
        """Format failure message.

        Args:
            excinfo: Exception info

        Returns:
            Formatted failure lines
        """
        lines = super().repr_failure(excinfo)
        if self.scenario:
            lines.insert(0, f"Scenario: {self.scenario.scenario_id}")
            if self.edge_case:
                lines.insert(1, f"Edge Case: {self.edge_case.get('case_id')}")
        return lines


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    """Generate coverage report after test session.

    Args:
        session: Pytest session
        exitstatus: Exit status code
    """
    # Check if coverage report was requested
    if session.config.getoption("--stress-coverage-report"):
        tracker = CoverageTracker()

        # Generate and print report
        report = tracker.generate_coverage_report()

        logger.info("\n" + "=" * 80)
        logger.info("STRESS TEST COVERAGE REPORT")
        logger.info("=" * 80)
        logger.info(f"Total scenarios: {report['total_scenarios']}")
        logger.info(f"Total runs: {report['total_runs']}")
        logger.info(f"Overall failure rate: {report['overall_failure_rate']:.1%}")
        logger.info(f"Average confidence: {report['avg_confidence']:.2f}")
        logger.info(f"\nGaps: {report['gap_summary']['total_gaps']}")
        logger.info(f"High priority gaps: {report['gap_summary']['high_priority_gaps']}")
        logger.info("=" * 80 + "\n")

        # Save report to file
        report_path = "stress_coverage_report.json"
        tracker.generate_coverage_report(output_path=report_path)
        logger.info(f"Coverage report saved to {report_path}")
