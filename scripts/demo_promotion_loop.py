#!/usr/bin/env python3
"""
Demonstration: Phase 0 - Close the Causal Loop
==============================================

Shows the complete promotion lifecycle:
1. Stress test runs accumulate
2. Check promotion eligibility
3. Execute promotion (update RESOURCE_LIMITS)
4. Simulate failure and rollback
5. Create regression scenario
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from quintet.stress.coverage import CoverageTracker
from quintet.stress.promotion import StressPromotionManager, PromotionDecision
from quintet.core.types import RESOURCE_LIMITS


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def main():
    print_section("Phase 0: Close the Causal Loop - Real Edition")

    # Initialize components
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    tracker = CoverageTracker(db_path)
    manager = StressPromotionManager(tracker)

    print("Initialized StressPromotionManager with temporary database")

    # 1. Simulate stress test runs
    print_section("Step 1: Accumulate Stress Test Runs")

    tracker.record_scenario(
        scenario_id="tolerance_sweep",
        name="Tolerance Parameter Sweep",
        category="parameter_exploration",
        domain="algebra"
    )

    print("Recording 25 stress test runs for 'tolerance_sweep' scenario...")
    for i in range(25):
        passed = i < 24  # 24 pass, 1 fails
        tracker.record_run({
            "run_id": f"run-{i:03d}",
            "scenario_id": "tolerance_sweep",
            "case_id": f"case-{i}",
            "passed": passed,
            "confidence": 0.82 if passed else 0.45,
            "outcome": "success" if passed else "failed",
            "duration_ms": 150.0,
            "budget_used": {"tier": "standard"}
        })

    stats = tracker.get_scenario_stats("tolerance_sweep")
    print(f"  Total runs: {stats['total_runs']}")
    print(f"  Passed: {stats['passed_runs']}")
    print(f"  Failure rate: {stats['failure_rate']:.1%}")
    print(f"  Avg confidence: {stats['avg_confidence']:.2f}")

    # 2. Check promotion eligibility
    print_section("Step 2: Check Promotion Eligibility")

    decision = manager.check_promotion_eligibility(
        scenario_id="tolerance_sweep",
        min_runs=20,
        max_failure_rate=0.15,
        min_avg_confidence=0.60
    )

    print(f"Eligible: {decision.eligible}")
    print(f"Confidence Score: {decision.confidence_score:.2f}")
    print(f"\nReason:\n{decision.reason}")

    if not decision.eligible:
        print("\nScenario not eligible for promotion. Exiting.")
        return

    # 3. Execute promotion
    print_section("Step 3: Execute Promotion (Update RESOURCE_LIMITS)")

    original_time = RESOURCE_LIMITS["standard"].max_wall_time_ms
    print(f"Original max_wall_time_ms (standard): {original_time}")

    policy_changes = {
        "standard": {
            "max_wall_time_ms": original_time + 15000  # Increase by 15 seconds
        }
    }

    action = manager.execute_promotion(
        scenario_id="tolerance_sweep",
        decision=decision,
        policy_changes=policy_changes
    )

    new_time = RESOURCE_LIMITS["standard"].max_wall_time_ms
    print(f"New max_wall_time_ms (standard): {new_time}")
    print(f"Change: +{new_time - original_time}ms")
    print(f"\nPromotion executed: {action.action}")
    print(f"Executed at: {action.executed_at}")

    # 4. Simulate failure and rollback
    print_section("Step 4: Simulate Metrics Degradation & Rollback")

    print("Simulating scenario: After promotion, timeout rate increased to 30%")
    print("Decision: Rollback to previous policy\n")

    rollback_action = manager.rollback_promotion(
        scenario_id="tolerance_sweep",
        reason="Timeout rate increased to 30% after promotion (exceeds 20% threshold)"
    )

    restored_time = RESOURCE_LIMITS["standard"].max_wall_time_ms
    print(f"Rolled back max_wall_time_ms (standard): {restored_time}")
    print(f"Matches original: {restored_time == original_time}")
    print(f"\nRollback reason: {rollback_action.reason}")

    # 5. Create regression scenario
    print_section("Step 5: Create Regression Scenario (Feedback Loop)")

    regression = manager.create_regression_scenario(
        failed_scenario_id="tolerance_sweep",
        failure_reason="Timeout rate increased to 30% after max_wall_time_ms promotion"
    )

    print(f"Created regression scenario: {regression['scenario_id']}")
    print(f"Category: {regression['category']}")
    print(f"Tags: {', '.join(regression['tags'])}")
    print(f"\nPromotion criteria (stricter):")
    print(f"  Min runs: {regression['promotion_config']['min_runs']}")
    print(f"  Max failure rate: {regression['promotion_config']['max_failure_rate']:.1%}")
    print(f"\nThis scenario will prevent us from promoting similar changes in the future.")

    # 6. Show audit trail
    print_section("Step 6: Audit Trail")

    history = manager.get_promotion_history()
    print(f"Total actions recorded: {len(history)}\n")

    for i, entry in enumerate(history, 1):
        print(f"{i}. Action: {entry['action']}")
        print(f"   Scenario: {entry['scenario_id']}")
        print(f"   Executed: {entry['executed_at']}")
        print(f"   Reason: {entry['reason']}")
        print()

    print_section("Summary")
    print("Phase 0 Complete: The causal loop is now closed!")
    print()
    print("What happened:")
    print("  1. Stress tests ran and accumulated statistics")
    print("  2. System checked promotion eligibility (passed)")
    print("  3. System executed promotion (actually changed RESOURCE_LIMITS)")
    print("  4. Metrics degraded, system detected and rolled back")
    print("  5. System created a regression scenario to prevent repeat")
    print("  6. All actions logged to audit trail")
    print()
    print("The system now learns from its mistakes and prevents bad promotions!")


if __name__ == "__main__":
    main()
