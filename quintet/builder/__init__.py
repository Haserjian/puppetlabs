"""
Build Mode (Ultra Mode 2.0)
============================

Project-aware builder with OODA loop, validation, and rollback.

Components:
- BuilderDetector: Detects build intent
- SpecGenerator: Context-aware spec generation
- BuilderExecutor: Executes builds with validation
- UltraModeOrchestrator: OODA loop orchestrator
- BuildAPI: HTTP API server
"""

from quintet.builder.types import (
    BuildIntent,
    FileSpec,
    ProjectContext,
    ProjectBlueprint,
    BuildResult,
)
from quintet.builder.detector import BuilderDetector
from quintet.builder.specification import SpecGenerator
from quintet.builder.executor import BuilderExecutor
from quintet.builder.ultra_mode import UltraModeOrchestrator, create_build_mode

__all__ = [
    "BuildIntent",
    "FileSpec",
    "ProjectContext",
    "ProjectBlueprint",
    "BuildResult",
    "BuilderDetector",
    "SpecGenerator",
    "BuilderExecutor",
    "UltraModeOrchestrator",
    "create_build_mode",
]


