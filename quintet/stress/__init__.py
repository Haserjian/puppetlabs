"""
Stress Testing Infrastructure
=============================

Declarative YAML-based stress testing with coverage tracking,
edge case management, and promotion eligibility assessment.

Core modules:
- scenario: StressScenario for YAML-based test definitions
- executor: StressExecutor for running stress tests with budget enforcement
- coverage: CoverageTracker for SQLite-based persistence and analysis
- edge_cases: EdgeCaseRegistry for domain-specific edge case management
- pytest_plugin: Pytest integration for automatic scenario discovery
- decorator: Unit-level stress testing decorator
- promotion: StressPromotionManager for shadow → production decisions
"""

from quintet.stress.scenario import StressScenario
from quintet.stress.executor import StressExecutor, StressTestResult, TimeoutException
from quintet.stress.coverage import CoverageTracker, CoverageGap

__all__ = [
    "StressScenario",
    "StressExecutor",
    "StressTestResult",
    "TimeoutException",
    "CoverageTracker",
    "CoverageGap",
]
