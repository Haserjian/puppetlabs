"""
Stress Test Coverage Tracking
=============================

SQLite-based persistence and analysis of stress test runs,
gap detection, and promotion eligibility.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from pathlib import Path
import sqlite3
import json
import threading
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CoverageGap:
    """Coverage gap identified from test results."""

    gap_id: str
    scenario_id: str
    gap_type: str  # "untested" | "low_confidence" | "high_failure_rate"
    description: str
    priority: int  # 1-5, higher is more urgent
    discovered_at: str
    resolved_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class CoverageTracker:
    """Thread-safe SQLite-based coverage tracking."""

    def __init__(self, db_path: str = "quintet/stress/coverage.db"):
        """Initialize coverage tracker.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Scenarios table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS scenarios (
                    scenario_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT,
                    domain TEXT,
                    total_runs INTEGER DEFAULT 0,
                    passed_runs INTEGER DEFAULT 0,
                    avg_confidence REAL DEFAULT 0.0,
                    last_run_at TEXT,
                    created_at TEXT
                )
                """
            )

            # Test runs table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS test_runs (
                    run_id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    budget_tier TEXT,
                    tolerance_config TEXT,
                    passed BOOLEAN,
                    confidence REAL,
                    duration_ms REAL,
                    outcome TEXT,
                    failure_reason TEXT,
                    warnings TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (scenario_id) REFERENCES scenarios(scenario_id)
                )
                """
            )

            # Coverage gaps table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS coverage_gaps (
                    gap_id TEXT PRIMARY KEY,
                    scenario_id TEXT NOT NULL,
                    gap_type TEXT,
                    description TEXT,
                    priority INTEGER,
                    discovered_at TEXT,
                    resolved_at TEXT,
                    FOREIGN KEY (scenario_id) REFERENCES scenarios(scenario_id)
                )
                """
            )

            # Create indexes
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_scenario ON test_runs(scenario_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON test_runs(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_gaps_scenario ON coverage_gaps(scenario_id)"
            )

            conn.commit()

        logger.info(f"Initialized coverage database: {self.db_path}")

    def record_scenario(self, scenario_id: str, name: str, category: str, domain: str) -> None:
        """Register a scenario for tracking.

        Args:
            scenario_id: Unique scenario identifier
            name: Human-readable scenario name
            category: Scenario category (edge_cases, budget_sweep, etc.)
            domain: Problem domain (algebra, calculus, etc.)
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO scenarios
                    (scenario_id, name, category, domain, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (scenario_id, name, category, domain, datetime.utcnow().isoformat())
                )

                conn.commit()

    def record_run(self, run_data: Dict[str, Any]) -> None:
        """Record a stress test run.

        Args:
            run_data: Test result data including run_id, scenario_id, case_id, etc.
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Insert test run
                cursor.execute(
                    """
                    INSERT INTO test_runs
                    (run_id, scenario_id, case_id, budget_tier, tolerance_config,
                     passed, confidence, duration_ms, outcome, failure_reason,
                     warnings, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_data.get("run_id"),
                        run_data.get("scenario_id"),
                        run_data.get("case_id"),
                        run_data.get("budget_used", {}).get("tier"),
                        json.dumps(run_data.get("tolerance_used", {})),
                        run_data.get("passed", False),
                        run_data.get("confidence", 0.0),
                        run_data.get("duration_ms", 0.0),
                        run_data.get("outcome"),
                        run_data.get("failure_reason"),
                        json.dumps(run_data.get("warnings", [])),
                        run_data.get("timestamp", datetime.utcnow().isoformat())
                    )
                )

                # Update scenario stats
                self._update_scenario_stats(cursor, run_data.get("scenario_id"))

                conn.commit()

    def _update_scenario_stats(self, cursor: sqlite3.Cursor, scenario_id: str) -> None:
        """Update scenario statistics after new run.

        Args:
            cursor: Database cursor
            scenario_id: Scenario ID
        """
        cursor.execute(
            """
            SELECT COUNT(*), SUM(CAST(passed AS INT)), AVG(confidence)
            FROM test_runs
            WHERE scenario_id = ?
            """,
            (scenario_id,)
        )

        row = cursor.fetchone()
        if row:
            total_runs, passed_runs, avg_confidence = row
            passed_runs = passed_runs or 0
            avg_confidence = avg_confidence or 0.0

            cursor.execute(
                """
                UPDATE scenarios
                SET total_runs = ?, passed_runs = ?, avg_confidence = ?, last_run_at = ?
                WHERE scenario_id = ?
                """,
                (total_runs, passed_runs, avg_confidence, datetime.utcnow().isoformat(), scenario_id)
            )

    def get_scenario_stats(self, scenario_id: str) -> Dict[str, Any]:
        """Get statistics for a scenario.

        Args:
            scenario_id: Scenario ID

        Returns:
            Dictionary with total_runs, passed_runs, avg_confidence, last_run_at
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT total_runs, passed_runs, avg_confidence, last_run_at
                FROM scenarios
                WHERE scenario_id = ?
                """,
                (scenario_id,)
            )

            row = cursor.fetchone()
            if row:
                return {
                    "total_runs": row[0] or 0,
                    "passed_runs": row[1] or 0,
                    "avg_confidence": row[2] or 0.0,
                    "last_run_at": row[3],
                    "failure_rate": 1.0 - ((row[1] or 0) / (row[0] or 1))
                }

        return {
            "total_runs": 0,
            "passed_runs": 0,
            "avg_confidence": 0.0,
            "last_run_at": None,
            "failure_rate": 1.0
        }

    def get_coverage_gaps(self, priority_min: int = 1) -> List[CoverageGap]:
        """Get unresolved coverage gaps.

        Args:
            priority_min: Minimum priority level (1-5)

        Returns:
            List of CoverageGap objects
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT gap_id, scenario_id, gap_type, description, priority, discovered_at, resolved_at
                FROM coverage_gaps
                WHERE resolved_at IS NULL AND priority >= ?
                ORDER BY priority DESC, discovered_at ASC
                """,
                (priority_min,)
            )

            gaps = []
            for row in cursor.fetchall():
                gaps.append(
                    CoverageGap(
                        gap_id=row[0],
                        scenario_id=row[1],
                        gap_type=row[2],
                        description=row[3],
                        priority=row[4],
                        discovered_at=row[5],
                        resolved_at=row[6]
                    )
                )

            return gaps

    def record_gap(self, gap: CoverageGap) -> None:
        """Record a coverage gap.

        Args:
            gap: CoverageGap instance
        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO coverage_gaps
                    (gap_id, scenario_id, gap_type, description, priority, discovered_at, resolved_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        gap.gap_id,
                        gap.scenario_id,
                        gap.gap_type,
                        gap.description,
                        gap.priority,
                        gap.discovered_at,
                        gap.resolved_at
                    )
                )

                conn.commit()

    def generate_coverage_report(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive coverage report.

        Args:
            output_path: Optional path to save JSON report

        Returns:
            Dictionary with scenario stats, gaps, and summary
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get all scenarios
            cursor.execute(
                """
                SELECT scenario_id, name, category, domain, total_runs, passed_runs, avg_confidence
                FROM scenarios
                ORDER BY category, domain, name
                """
            )

            scenarios = []
            total_runs = 0
            total_passed = 0
            total_avg_confidence = 0.0

            for row in cursor.fetchall():
                scenario_id, name, category, domain, runs, passed, avg_conf = row
                scenario_stats = {
                    "scenario_id": scenario_id,
                    "name": name,
                    "category": category,
                    "domain": domain,
                    "total_runs": runs or 0,
                    "passed_runs": passed or 0,
                    "failure_rate": 1.0 - ((passed or 0) / (runs or 1)) if runs else 1.0,
                    "avg_confidence": avg_conf or 0.0
                }
                scenarios.append(scenario_stats)
                total_runs += (runs or 0)
                total_passed += (passed or 0)
                total_avg_confidence += (avg_conf or 0.0)

            # Get gaps
            gaps = self.get_coverage_gaps()

            report = {
                "generated_at": datetime.utcnow().isoformat(),
                "total_scenarios": len(scenarios),
                "total_runs": total_runs,
                "total_passed": total_passed,
                "overall_failure_rate": 1.0 - (total_passed / total_runs) if total_runs else 1.0,
                "avg_confidence": (total_avg_confidence / len(scenarios)) if scenarios else 0.0,
                "scenarios": scenarios,
                "gaps": [gap.to_dict() for gap in gaps],
                "gap_summary": {
                    "total_gaps": len(gaps),
                    "by_type": self._count_gaps_by_type(gaps),
                    "high_priority_gaps": len([g for g in gaps if g.priority >= 4])
                }
            }

            if output_path:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w") as f:
                    json.dump(report, f, indent=2)
                logger.info(f"Coverage report saved to {output_path}")

            return report

    @staticmethod
    def _count_gaps_by_type(gaps: List[CoverageGap]) -> Dict[str, int]:
        """Count gaps by type.

        Args:
            gaps: List of CoverageGap objects

        Returns:
            Dictionary mapping gap type to count
        """
        counts = {}
        for gap in gaps:
            counts[gap.gap_type] = counts.get(gap.gap_type, 0) + 1
        return counts
