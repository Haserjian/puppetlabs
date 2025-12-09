"""
Tests for Stress Testing Infrastructure
========================================

Comprehensive tests for stress DSL components including scenario management,
executor, coverage tracking, edge cases, and promotion.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from quintet.stress.scenario import StressScenario
from quintet.stress.executor import StressExecutor, StressTestResult, TimeoutException
from quintet.stress.coverage import CoverageTracker, CoverageGap
from quintet.stress.edge_cases import (
    EdgeCase, EdgeCaseRegistry, get_edge_case_registry, register_edge_case
)
from quintet.stress.promotion import StressPromotionManager, PromotionDecision
from quintet.stress.decorator import stress_test, mark_stress_test_coverage


class TestStressScenario:
    """Tests for StressScenario."""

    def test_scenario_creation(self):
        """Create a stress scenario programmatically."""
        scenario = StressScenario(
            scenario_id="test-001",
            name="Test Scenario",
            description="Test scenario description",
            category="edge_cases",
            domain="algebra",
            tags=["test", "overflow"],
            edge_cases=[
                {
                    "case_id": "overflow_1",
                    "category": "overflow",
                    "description": "Overflow test",
                    "problem": {"type": "solve"}
                }
            ]
        )

        assert scenario.scenario_id == "test-001"
        assert scenario.category == "edge_cases"
        assert len(scenario.edge_cases) == 1

    def test_scenario_yaml_loading(self):
        """Load scenario from YAML file."""
        yaml_content = """
scenario_id: "test-scenario"
name: "Test Scenario"
description: "Test"
category: "edge_cases"
domain: "algebra"
tags: ["test"]
edge_cases:
  - case_id: "case_1"
    category: "overflow"
    problem: {"type": "solve"}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                scenario = StressScenario.from_yaml(f.name)
                assert scenario.scenario_id == "test-scenario"
                assert len(scenario.edge_cases) == 1
            finally:
                Path(f.name).unlink()

    def test_scenario_to_dict(self):
        """Convert scenario to dictionary."""
        scenario = StressScenario(
            scenario_id="test-001",
            name="Test",
            description="Test",
            category="edge_cases",
            domain="algebra"
        )

        data = scenario.to_dict()
        assert data["scenario_id"] == "test-001"
        assert "stress_config" in data

    def test_scenario_get_edge_cases(self):
        """Get edge cases with filtering."""
        scenario = StressScenario(
            scenario_id="test-001",
            name="Test",
            description="Test",
            category="edge_cases",
            domain="algebra",
            edge_cases=[
                {"case_id": "case_1", "category": "overflow"},
                {"case_id": "case_2", "category": "underflow"},
                {"case_id": "case_3", "category": "overflow"}
            ]
        )

        overflow_cases = scenario.get_edge_cases(category="overflow")
        assert len(overflow_cases) == 2
        assert all(c["category"] == "overflow" for c in overflow_cases)

    def test_scenario_get_budget_tiers(self):
        """Get budget tiers from scenario."""
        scenario = StressScenario(
            scenario_id="test-001",
            name="Test",
            description="Test",
            category="edge_cases",
            domain="algebra",
            stress_config={
                "budget_tiers": [
                    {"tier": "light"},
                    {"tier": "standard"},
                    {"tier": "deep_search"}
                ]
            }
        )

        tiers = scenario.get_budget_tiers()
        assert tiers == ["light", "standard", "deep_search"]

    def test_scenario_promotion_config(self):
        """Access promotion configuration."""
        scenario = StressScenario(
            scenario_id="test-001",
            name="Test",
            description="Test",
            category="edge_cases",
            domain="algebra",
            promotion_config={
                "shadow_mode": True,
                "promotion_criteria": {
                    "min_runs": 10,
                    "max_failure_rate": 0.10
                }
            }
        )

        assert scenario.is_promotion_enabled()
        criteria = scenario.get_promotion_criteria()
        assert criteria["min_runs"] == 10


class TestStressExecutor:
    """Tests for StressExecutor."""

    @pytest.fixture
    def executor(self):
        """Create executor."""
        return StressExecutor()

    @pytest.fixture
    def sample_scenario(self):
        """Create sample scenario."""
        return StressScenario(
            scenario_id="test-001",
            name="Test",
            description="Test",
            category="edge_cases",
            domain="algebra",
            edge_cases=[
                {
                    "case_id": "test_case",
                    "problem": {"type": "solve", "expected_result": {"success": True}},
                    "expected_result": {"outcome": "success", "confidence_min": 0.5}
                }
            ]
        )

    def test_executor_initialization(self, executor):
        """Executor initializes correctly."""
        assert executor is not None
        assert executor.validator is not None

    def test_run_stress_test_success(self, executor, sample_scenario):
        """Execute stress test successfully."""
        result = executor.run_stress_test(
            scenario=sample_scenario,
            edge_case=sample_scenario.edge_cases[0],
            budget_tier="standard"
        )

        assert isinstance(result, StressTestResult)
        assert result.scenario_id == "test-001"
        assert result.case_id == "test_case"
        assert result.run_id is not None
        assert result.duration_ms > 0

    def test_run_stress_test_invalid_tier(self, executor, sample_scenario):
        """Handle invalid budget tier gracefully."""
        result = executor.run_stress_test(
            scenario=sample_scenario,
            edge_case=sample_scenario.edge_cases[0],
            budget_tier="invalid_tier"
        )

        assert result is not None
        # Should fall back to "standard"
        assert "budget_used" in result.to_dict()

    def test_stress_test_result_to_dict(self):
        """Convert result to dictionary."""
        result = StressTestResult(
            run_id="run-001",
            scenario_id="scenario-001",
            case_id="case-001",
            passed=True,
            confidence=0.85,
            duration_ms=100.0,
            outcome="success"
        )

        data = result.to_dict()
        assert data["run_id"] == "run-001"
        assert data["passed"] is True
        assert data["outcome"] == "success"


class TestCoverageTracker:
    """Tests for CoverageTracker."""

    @pytest.fixture
    def tracker(self):
        """Create tracker with temp database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            yield CoverageTracker(str(db_path))

    def test_tracker_initialization(self, tracker):
        """Tracker initializes with schema."""
        assert tracker is not None

    def test_record_scenario(self, tracker):
        """Record a scenario."""
        tracker.record_scenario(
            scenario_id="test-001",
            name="Test Scenario",
            category="edge_cases",
            domain="algebra"
        )

        stats = tracker.get_scenario_stats("test-001")
        assert stats["total_runs"] == 0

    def test_record_run(self, tracker):
        """Record a test run."""
        tracker.record_scenario(
            scenario_id="test-001",
            name="Test",
            category="edge_cases",
            domain="algebra"
        )

        tracker.record_run({
            "run_id": "run-001",
            "scenario_id": "test-001",
            "case_id": "case-001",
            "passed": True,
            "confidence": 0.85,
            "duration_ms": 100.0,
            "outcome": "success",
            "budget_used": {"tier": "standard"}
        })

        stats = tracker.get_scenario_stats("test-001")
        assert stats["total_runs"] == 1
        assert stats["passed_runs"] == 1

    def test_scenario_stats_computation(self, tracker):
        """Compute scenario statistics."""
        tracker.record_scenario(
            scenario_id="test-001",
            name="Test",
            category="edge_cases",
            domain="algebra"
        )

        # Record multiple runs
        for i in range(5):
            tracker.record_run({
                "run_id": f"run-00{i}",
                "scenario_id": "test-001",
                "case_id": f"case-{i}",
                "passed": i < 4,  # 4 pass, 1 fails
                "confidence": 0.8 - (0.2 if i == 4 else 0),
                "outcome": "success" if i < 4 else "failed",
                "budget_used": {"tier": "standard"}
            })

        stats = tracker.get_scenario_stats("test-001")
        assert stats["total_runs"] == 5
        assert stats["passed_runs"] == 4
        assert stats["failure_rate"] == pytest.approx(0.2, abs=0.01)

    def test_coverage_report_generation(self, tracker):
        """Generate coverage report."""
        tracker.record_scenario(
            scenario_id="test-001",
            name="Test",
            category="edge_cases",
            domain="algebra"
        )

        tracker.record_run({
            "run_id": "run-001",
            "scenario_id": "test-001",
            "case_id": "case-001",
            "passed": True,
            "confidence": 0.85,
            "outcome": "success",
            "budget_used": {"tier": "standard"}
        })

        report = tracker.generate_coverage_report()
        assert "total_scenarios" in report
        assert "total_runs" in report
        assert report["total_scenarios"] == 1
        assert report["total_runs"] == 1


class TestEdgeCaseRegistry:
    """Tests for EdgeCaseRegistry."""

    @pytest.fixture
    def registry(self):
        """Create registry."""
        return EdgeCaseRegistry()

    def test_registry_creation(self, registry):
        """Create edge case registry."""
        assert registry is not None

    def test_register_edge_case(self, registry):
        """Register an edge case."""
        case = EdgeCase(
            case_id="overflow_1",
            domain="algebra",
            category="overflow",
            description="Overflow test",
            tags=["numeric"]
        )

        registry.register(domain="algebra", case=case)

        cases = registry.get_cases(domain="algebra")
        assert len(cases) == 1
        assert cases[0].case_id == "overflow_1"

    def test_filter_by_category(self, registry):
        """Filter edge cases by category."""
        for i, category in enumerate(["overflow", "underflow", "overflow"]):
            case = EdgeCase(
                case_id=f"case_{category}_{i}",  # Make IDs unique to avoid overwrites
                domain="algebra",
                category=category,
                description="Test",
                tags=[]
            )
            registry.register("algebra", case)

        overflow_cases = registry.get_cases("algebra", category="overflow")
        assert len(overflow_cases) == 2

    def test_list_categories(self, registry):
        """List categories for domain."""
        for category in ["overflow", "underflow", "singularity"]:
            case = EdgeCase(
                case_id=f"case_{category}",
                domain="algebra",
                category=category,
                description="Test",
                tags=[]
            )
            registry.register("algebra", case)

        categories = registry.list_categories("algebra")
        assert set(categories) == {"overflow", "underflow", "singularity"}

    def test_builtin_edge_cases(self):
        """Built-in edge cases are registered."""
        registry = get_edge_case_registry()

        algebra_cases = registry.get_cases("algebra")
        assert len(algebra_cases) > 0

        # Check for specific built-in cases
        case_ids = [c.case_id for c in algebra_cases]
        assert "overflow_quadratic" in case_ids
        assert "underflow_quadratic" in case_ids


class TestPromotionManager:
    """Tests for StressPromotionManager."""

    @pytest.fixture
    def promotion_manager(self):
        """Create promotion manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            tracker = CoverageTracker(str(db_path))
            yield StressPromotionManager(tracker)

    def test_promotion_initialization(self, promotion_manager):
        """Initialize promotion manager."""
        assert promotion_manager is not None
        assert promotion_manager.tracker is not None

    def test_promotion_eligibility_insufficient_runs(self, promotion_manager):
        """Check eligibility with insufficient runs."""
        promotion_manager.tracker.record_scenario(
            scenario_id="test-001",
            name="Test",
            category="edge_cases",
            domain="algebra"
        )

        decision = promotion_manager.check_promotion_eligibility(
            scenario_id="test-001",
            min_runs=20
        )

        assert decision.eligible is False
        assert "Insufficient runs" in decision.reason

    def test_promotion_eligibility_high_failure_rate(self, promotion_manager):
        """Check eligibility with high failure rate."""
        promotion_manager.tracker.record_scenario(
            scenario_id="test-001",
            name="Test",
            category="edge_cases",
            domain="algebra"
        )

        # Record 10 runs, 7 fail
        for i in range(10):
            promotion_manager.tracker.record_run({
                "run_id": f"run-{i:03d}",
                "scenario_id": "test-001",
                "case_id": f"case-{i}",
                "passed": i < 3,  # Only 3 pass
                "confidence": 0.8,
                "outcome": "success" if i < 3 else "failed",
                "budget_used": {"tier": "standard"}
            })

        decision = promotion_manager.check_promotion_eligibility(
            scenario_id="test-001",
            min_runs=5,
            max_failure_rate=0.5
        )

        assert decision.eligible is False
        assert "Failure rate" in decision.reason

    def test_promotion_eligibility_eligible(self, promotion_manager):
        """Check eligibility when all criteria met."""
        promotion_manager.tracker.record_scenario(
            scenario_id="test-001",
            name="Test",
            category="edge_cases",
            domain="algebra"
        )

        # Record 20 runs, all pass
        for i in range(20):
            promotion_manager.tracker.record_run({
                "run_id": f"run-{i:03d}",
                "scenario_id": "test-001",
                "case_id": f"case-{i}",
                "passed": True,
                "confidence": 0.85,
                "outcome": "success",
                "budget_used": {"tier": "standard"}
            })

        decision = promotion_manager.check_promotion_eligibility(
            scenario_id="test-001",
            min_runs=20,
            max_failure_rate=0.15,
            min_avg_confidence=0.60
        )

        assert decision.eligible is True
        assert decision.confidence_score > 0.5

    def test_promotion_summary(self, promotion_manager):
        """Get promotion readiness summary."""
        # Create multiple scenarios with different readiness
        for scenario_num in range(3):
            promotion_manager.tracker.record_scenario(
                scenario_id=f"scenario-{scenario_num:03d}",
                name=f"Scenario {scenario_num}",
                category="edge_cases",
                domain="algebra"
            )

            # Vary number of runs and pass rate
            num_runs = 15 + (scenario_num * 5)
            pass_rate = 0.5 + (scenario_num * 0.2)

            for i in range(num_runs):
                promotion_manager.tracker.record_run({
                    "run_id": f"run-{scenario_num}-{i:03d}",
                    "scenario_id": f"scenario-{scenario_num:03d}",
                    "case_id": f"case-{i}",
                    "passed": i < int(num_runs * pass_rate),
                    "confidence": 0.7 + (scenario_num * 0.1),
                    "outcome": "success",
                    "budget_used": {"tier": "standard"}
                })

        summary = promotion_manager.get_promotion_summary()
        assert "ready_for_promotion" in summary
        assert "near_promotion_ready" in summary
        assert "not_ready" in summary


class TestStressDecorator:
    """Tests for stress test decorator."""

    def test_stress_test_decorator(self):
        """Apply stress test decorator."""

        @stress_test(
            scenario_id="test-scenario",
            edge_cases=[
                {"case_id": "case_1"},
                {"case_id": "case_2"}
            ]
        )
        def sample_test():
            return {"passed": True, "confidence": 0.85}

        assert hasattr(sample_test, "__stress_test__")
        assert sample_test.__stress_test__["scenario_id"] == "test-scenario"
        assert len(sample_test.__stress_test__["edge_cases"]) == 2

    def test_mark_coverage_decorator(self):
        """Apply mark_stress_test_coverage decorator."""

        @mark_stress_test_coverage(
            scenario_id="test-scenario",
            case_id="case_1",
            priority=4
        )
        def test_function():
            return True

        assert hasattr(test_function, "__mark_coverage__")
        assert test_function.__mark_coverage__["priority"] == 4
