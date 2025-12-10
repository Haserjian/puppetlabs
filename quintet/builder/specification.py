"""
Build Mode Spec Generator
==========================

Context-aware specification generator.
Scans project, detects patterns, and generates blueprints.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime

from quintet.builder.types import (
    BuildIntent, BuildCategory, ProjectContext, FileInfo,
    ProjectBlueprint, FileSpec, ShellCommand, TestPlan, RiskAssessment
)
from quintet.core.types import ContextFlowEntry, IncompletenessAssessment


class SpecGenerator:
    """
    Generates project blueprints from build intents.
    
    Scans the project directory to understand context before generating specs.
    """
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or os.getcwd()
    
    def scan_project(self, root: Optional[str] = None) -> ProjectContext:
        """
        Scan project directory and gather context.
        """
        root = root or self.project_root
        root_path = Path(root)
        
        existing_files = []
        detected_frameworks = []
        detected_patterns = []
        package_manager = None
        test_framework = None
        entry_points = []
        
        if not root_path.exists():
            return ProjectContext(project_root=root)
        
        # Scan for files (limit depth to avoid huge scans)
        for item in self._walk_limited(root_path, max_depth=3, max_files=100):
            if item.is_file():
                file_info = self._analyze_file(item, root_path)
                if file_info:
                    existing_files.append(file_info)
        
        # Detect package manager
        if (root_path / "requirements.txt").exists():
            package_manager = "pip"
            detected_frameworks.append("python")
        if (root_path / "pyproject.toml").exists():
            package_manager = "pip"
            detected_frameworks.append("python")
        if (root_path / "package.json").exists():
            package_manager = "npm"
            detected_frameworks.append("nodejs")
        if (root_path / "Cargo.toml").exists():
            package_manager = "cargo"
            detected_frameworks.append("rust")
        if (root_path / "go.mod").exists():
            package_manager = "go"
            detected_frameworks.append("go")
        
        # Detect test framework
        if (root_path / "pytest.ini").exists() or (root_path / "tests").is_dir():
            test_framework = "pytest"
        if (root_path / "jest.config.js").exists():
            test_framework = "jest"
        
        # Detect patterns
        if any("fastapi" in str(f.path).lower() for f in existing_files):
            detected_patterns.append("fastapi")
        if any("api" in str(f.path).lower() for f in existing_files):
            detected_patterns.append("api")
        if (root_path / "src").is_dir():
            detected_patterns.append("src-layout")
        
        # Find entry points
        for name in ["main.py", "app.py", "__main__.py", "index.js", "main.go", "main.rs"]:
            if (root_path / name).exists():
                entry_points.append(name)
            if (root_path / "src" / name).exists():
                entry_points.append(f"src/{name}")
        
        return ProjectContext(
            project_root=root,
            existing_files=existing_files,
            detected_frameworks=list(set(detected_frameworks)),
            detected_patterns=detected_patterns,
            package_manager=package_manager,
            test_framework=test_framework,
            entry_points=entry_points
        )
    
    def generate_blueprint(
        self,
        intent: BuildIntent,
        context: Optional[ProjectContext] = None,
        synthesis: Optional[Dict[str, Any]] = None
    ) -> ProjectBlueprint:
        """
        Generate a project blueprint from intent and context.
        """
        if context is None:
            context = self.scan_project()
        
        # Generate based on category
        if intent.category == BuildCategory.CREATE_FILE:
            bp = self._blueprint_create_file(intent, context)
        elif intent.category == BuildCategory.CREATE_MODULE:
            bp = self._blueprint_create_module(intent, context)
        elif intent.category == BuildCategory.CREATE_PROJECT:
            bp = self._blueprint_create_project(intent, context)
        elif intent.category == BuildCategory.ADD_FEATURE:
            bp = self._blueprint_add_feature(intent, context)
        elif intent.category == BuildCategory.ADD_TESTS:
            bp = self._blueprint_add_tests(intent, context)
        elif intent.category == BuildCategory.FIX_BUG:
            bp = self._blueprint_fix_bug(intent, context)
        else:
            bp = self._blueprint_generic(intent, context)

        # Detect contradictions between intent and existing files
        contradictions = self._detect_contradictions(bp, context)
        bp.contradictions = contradictions
        
        # Attach flow / cognition metadata (minimal seed)
        bp.context_flow.extend(self._seed_flow(intent))
        
        # Log contradictions in flow if any
        if contradictions:
            from quintet.core.types import ContextFlowEntry
            from datetime import datetime
            bp.context_flow.append(ContextFlowEntry(
                timestamp=datetime.utcnow().isoformat(),
                phase="orient",
                source="contradiction_detector",
                target="blueprint",
                influence_type="constraint",
                weight=0.9,
                note=f"Detected {len(contradictions)} contradiction(s): {'; '.join(c[0] for c in contradictions[:3])}"
            ))
        
        # Assess incompleteness based on contradictions
        score = 0.5 if not contradictions else max(0.2, 0.5 - 0.1 * len(contradictions))
        missing = ["Validation pending"]
        if contradictions:
            missing.append(f"{len(contradictions)} contradiction(s) need resolution")
        
        bp.incompleteness = IncompletenessAssessment(
            score=score,
            missing_elements=missing,
            next_steps=["Resolve contradictions" if contradictions else "Execute blueprint", "Validate artifacts"],
            auto_approve_allowed=not contradictions  # Block auto-approve if contradictions exist
        )
        bp.next_steps = ["Resolve contradictions", "Execute blueprint", "Validate artifacts"] if contradictions else ["Execute blueprint", "Validate artifacts"]
        return bp
    
    def _blueprint_create_file(
        self,
        intent: BuildIntent,
        context: ProjectContext
    ) -> ProjectBlueprint:
        """Generate blueprint for creating a file."""
        files = []
        
        # Determine file path
        if intent.target_files:
            for path in intent.target_files:
                files.append(FileSpec(
                    path=path,
                    action="create",
                    content=self._generate_file_template(path, context),
                    description=f"Create {path}",
                    language=self._detect_language(path)
                ))
        else:
            # Default to a Python file
            path = "new_file.py"
            files.append(FileSpec(
                path=path,
                action="create",
                content='"""New module."""\n\n',
                description="Create new file",
                language="python"
            ))
        
        return ProjectBlueprint(
            goal=intent.description,
            description=f"Create file(s): {', '.join(f.path for f in files)}",
            files=files,
            context=context,
            risks=RiskAssessment(level="low", factors=["New file creation"])
        )
    
    def _blueprint_create_module(
        self,
        intent: BuildIntent,
        context: ProjectContext
    ) -> ProjectBlueprint:
        """Generate blueprint for creating a module."""
        files = []
        module_name = intent.target_modules[0] if intent.target_modules else "new_module"
        
        # Convert CamelCase to snake_case for directory
        dir_name = self._camel_to_snake(module_name)
        
        files.append(FileSpec(
            path=f"{dir_name}/__init__.py",
            action="create",
            content=f'"""{module_name} module."""\n\n__version__ = "0.1.0"\n',
            description=f"Create {module_name} package init",
            language="python"
        ))
        
        files.append(FileSpec(
            path=f"{dir_name}/core.py",
            action="create",
            content=f'"""{module_name} core functionality."""\n\n\nclass {module_name}:\n    """Main {module_name} class."""\n    \n    def __init__(self):\n        pass\n',
            description=f"Create {module_name} core",
            language="python"
        ))
        
        return ProjectBlueprint(
            goal=f"Create {module_name} module",
            description=f"Create module with {len(files)} files",
            files=files,
            context=context,
            risks=RiskAssessment(level="low", factors=["New module creation"])
        )
    
    def _blueprint_create_project(
        self,
        intent: BuildIntent,
        context: ProjectContext
    ) -> ProjectBlueprint:
        """Generate blueprint for creating a project."""
        files = []
        commands = []
        
        # Determine project type from technologies
        if "python" in intent.technologies or "fastapi" in str(intent.raw_query).lower():
            files.extend(self._python_project_files())
            commands.append(ShellCommand(
                command="pip install -r requirements.txt",
                description="Install dependencies",
                required=False
            ))
        else:
            # Default Python project
            files.extend(self._python_project_files())
        
        return ProjectBlueprint(
            goal="Create new project",
            description=f"Project scaffold with {len(files)} files",
            files=files,
            post_commands=commands,
            context=context,
            risks=RiskAssessment(level="medium", factors=["Project creation", "Dependency installation"])
        )
    
    def _blueprint_add_feature(
        self,
        intent: BuildIntent,
        context: ProjectContext
    ) -> ProjectBlueprint:
        """Generate blueprint for adding a feature."""
        return ProjectBlueprint(
            goal=intent.description,
            description="Add feature (files to be determined)",
            files=[],  # Would need more info to populate
            context=context,
            risks=RiskAssessment(level="medium", factors=["Modifying existing code"])
        )
    
    def _blueprint_add_tests(
        self,
        intent: BuildIntent,
        context: ProjectContext
    ) -> ProjectBlueprint:
        """Generate blueprint for adding tests."""
        files = []
        
        # Create tests directory if needed
        files.append(FileSpec(
            path="tests/__init__.py",
            action="create",
            content='"""Tests package."""\n',
            language="python"
        ))
        
        files.append(FileSpec(
            path="tests/test_main.py",
            action="create",
            content='"""Main test module."""\n\nimport pytest\n\n\ndef test_placeholder():\n    """Placeholder test."""\n    assert True\n',
            language="python"
        ))
        
        return ProjectBlueprint(
            goal="Add tests",
            description="Create test structure",
            files=files,
            post_commands=[
                ShellCommand(command="pytest tests/ -v", description="Run tests", required=False)
            ],
            test_plan=TestPlan(
                test_commands=[ShellCommand(command="pytest tests/ -v", description="Run all tests")]
            ),
            context=context,
            risks=RiskAssessment(level="low", factors=["Test creation"])
        )
    
    def _blueprint_fix_bug(
        self,
        intent: BuildIntent,
        context: ProjectContext
    ) -> ProjectBlueprint:
        """Generate blueprint for fixing a bug."""
        return ProjectBlueprint(
            goal=intent.description,
            description="Bug fix (analysis required)",
            files=[],  # Would need diagnosis first
            context=context,
            risks=RiskAssessment(level="medium", factors=["Code modification", "Potential side effects"])
        )
    
    def _blueprint_generic(
        self,
        intent: BuildIntent,
        context: ProjectContext
    ) -> ProjectBlueprint:
        """Generate generic blueprint."""
        return ProjectBlueprint(
            goal=intent.description,
            description="Generic build request",
            files=[],
            context=context,
            risks=RiskAssessment(level="low", factors=[]),
            context_flow=[],
            contradictions=[],
            recursion_seeds=[],
            recursion_postmortems=[],
            next_steps=[]
        )
    
    def _python_project_files(self) -> List[FileSpec]:
        """Generate files for a Python project."""
        return [
            FileSpec(
                path="README.md",
                action="create",
                content="# Project\n\nA new Python project.\n\n## Installation\n\n```bash\npip install -r requirements.txt\n```\n",
                language="markdown"
            ),
            FileSpec(
                path="requirements.txt",
                action="create",
                content="# Dependencies\npytest>=7.0\n",
                language="text"
            ),
            FileSpec(
                path="src/__init__.py",
                action="create",
                content='"""Main package."""\n',
                language="python"
            ),
            FileSpec(
                path="src/main.py",
                action="create",
                content='"""Main module."""\n\n\ndef main():\n    """Entry point."""\n    print("Hello, World!")\n\n\nif __name__ == "__main__":\n    main()\n',
                language="python"
            ),
            FileSpec(
                path="tests/__init__.py",
                action="create",
                content='"""Tests package."""\n',
                language="python"
            ),
        ]
    
    def _walk_limited(self, root: Path, max_depth: int, max_files: int) -> List[Path]:
        """Walk directory with limits."""
        results = []
        count = 0
        
        def _walk(path: Path, depth: int):
            nonlocal count
            if depth > max_depth or count >= max_files:
                return
            
            try:
                for item in path.iterdir():
                    if count >= max_files:
                        return
                    if item.name.startswith('.'):
                        continue
                    if item.name in ['__pycache__', 'node_modules', '.git', 'venv', '.venv']:
                        continue
                    
                    results.append(item)
                    count += 1
                    
                    if item.is_dir():
                        _walk(item, depth + 1)
            except PermissionError:
                pass
        
        _walk(root, 0)
        return results
    
    def _analyze_file(self, path: Path, root: Path) -> Optional[FileInfo]:
        """Analyze a single file."""
        try:
            rel_path = str(path.relative_to(root))
            size = path.stat().st_size
            language = self._detect_language(str(path))
            
            return FileInfo(
                path=rel_path,
                size_bytes=size,
                language=language
            )
        except Exception:
            return None
    
    def _detect_language(self, path: str) -> Optional[str]:
        """Detect language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".c": "c",
            ".h": "c",
            ".html": "html",
            ".css": "css",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".toml": "toml",
        }
        
        for ext, lang in ext_map.items():
            if path.endswith(ext):
                return lang
        return None
    
    def _generate_file_template(self, path: str, context: ProjectContext) -> str:
        """Generate a basic template for a file."""
        lang = self._detect_language(path)
        
        if lang == "python":
            return '"""Module docstring."""\n\n'
        elif lang == "javascript":
            return '// Module\n\n'
        elif lang == "typescript":
            return '// Module\n\n'
        else:
            return ""

    # ---------------------------------------------------------------------
    # Contradiction detection
    # ---------------------------------------------------------------------
    def _detect_contradictions(
        self,
        blueprint: ProjectBlueprint,
        context: ProjectContext
    ) -> List[tuple]:
        """
        Detect contradictions between blueprint and existing project.
        
        Returns list of (description, file_path, severity) tuples.
        """
        contradictions = []
        existing_paths = {f.path for f in context.existing_files}
        
        for file_spec in blueprint.files:
            if file_spec.action == "create":
                # Contradiction: creating a file that already exists
                if file_spec.path in existing_paths:
                    contradictions.append((
                        f"File '{file_spec.path}' already exists",
                        file_spec.path,
                        "warning"  # Could be overwrite, not fatal
                    ))
            
            elif file_spec.action == "modify":
                # Contradiction: modifying a file that doesn't exist
                if file_spec.path not in existing_paths:
                    contradictions.append((
                        f"Cannot modify '{file_spec.path}' - file does not exist",
                        file_spec.path,
                        "error"
                    ))
            
            elif file_spec.action == "delete":
                # Contradiction: deleting a file that doesn't exist
                if file_spec.path not in existing_paths:
                    contradictions.append((
                        f"Cannot delete '{file_spec.path}' - file does not exist",
                        file_spec.path,
                        "warning"  # Idempotent, not fatal
                    ))
        
        # Check for framework/pattern conflicts
        if blueprint.files:
            # E.g., creating React files in a Django project
            has_react = any("react" in f.path.lower() or "jsx" in f.path for f in blueprint.files)
            has_django = "django" in context.detected_frameworks
            if has_react and has_django and "react" not in context.detected_frameworks:
                contradictions.append((
                    "Adding React files to Django project without React setup",
                    "project",
                    "warning"
                ))
        
        return contradictions

    # ---------------------------------------------------------------------
    # Flow seeds
    # ---------------------------------------------------------------------
    def _seed_flow(self, intent: BuildIntent) -> List[ContextFlowEntry]:
        """Create a minimal context_flow seed so downstream UI/tiles can render."""
        now = datetime.utcnow().isoformat()
        return [
            ContextFlowEntry(
                timestamp=now,
                phase="observe",
                source="builder.detector",
                target="intent",
                influence_type="pattern",
                weight=intent.confidence,
                note=f"Detected build intent: {intent.category.value}"
            ),
            ContextFlowEntry(
                timestamp=now,
                phase="orient",
                source="spec_generator",
                target="blueprint",
                influence_type="heuristic",
                weight=0.8,
                note="Generated initial blueprint"
            ),
        ]
    
    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case."""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

