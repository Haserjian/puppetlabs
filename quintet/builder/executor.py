"""
Build Mode Executor
====================

Executes build blueprints with validation and rollback support.
"""

import os
import subprocess
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from quintet.core.types import (
    ValidationResult, ValidationCheck, ModeError, ErrorCode
)
from quintet.builder.types import (
    ProjectBlueprint, FileSpec, ShellCommand,
    FileResult, CommandResult
)


class BuilderExecutor:
    """
    Executes project blueprints.
    
    Features:
    - File creation/modification with validation
    - Shell command execution with timeout
    - Rollback support for failed builds
    """
    
    def __init__(
        self,
        project_root: Optional[str] = None,
        dry_run: bool = False,
        enable_rollback: bool = True
    ):
        self.project_root = Path(project_root or os.getcwd())
        self.dry_run = dry_run
        self.enable_rollback = enable_rollback
        self._rollback_data: Dict[str, Any] = {}
    
    def execute(
        self,
        blueprint: ProjectBlueprint,
        options: Optional[Dict[str, Any]] = None
    ) -> tuple[List[FileResult], List[CommandResult], ValidationResult]:
        """
        Execute a build blueprint.
        
        Returns:
            Tuple of (file_results, command_results, validation_result)
        """
        options = options or {}
        file_results = []
        command_results = []
        
        # Initialize rollback data
        if self.enable_rollback:
            self._rollback_data = {
                "files_created": [],
                "files_modified": {},
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            # Execute pre-commands
            for cmd in blueprint.pre_commands:
                result = self._execute_command(cmd)
                command_results.append(result)
                if not result.success and cmd.required:
                    return file_results, command_results, self._validation_failed(
                        f"Pre-command failed: {cmd.command}"
                    )
            
            # Execute file operations
            for file_spec in blueprint.files:
                result = self._execute_file_op(file_spec)
                file_results.append(result)
                if not result.success:
                    # Rollback and return
                    if self.enable_rollback:
                        self._rollback()
                    return file_results, command_results, self._validation_failed(
                        f"File operation failed: {file_spec.path}"
                    )
            
            # Execute post-commands
            for cmd in blueprint.post_commands:
                result = self._execute_command(cmd)
                command_results.append(result)
                if not result.success and cmd.required:
                    return file_results, command_results, self._validation_failed(
                        f"Post-command failed: {cmd.command}"
                    )
            
            # Validate the build
            validation = self._validate_build(blueprint, file_results)
            
            return file_results, command_results, validation
            
        except Exception as e:
            if self.enable_rollback:
                self._rollback()
            return file_results, command_results, self._validation_failed(str(e))
    
    def _execute_file_op(self, file_spec: FileSpec) -> FileResult:
        """Execute a single file operation."""
        path = self.project_root / file_spec.path
        
        if self.dry_run:
            return FileResult(
                path=file_spec.path,
                action=file_spec.action,
                success=True,
                bytes_written=len(file_spec.content) if file_spec.content else 0
            )
        
        try:
            if file_spec.action == "create":
                return self._create_file(path, file_spec)
            elif file_spec.action == "modify":
                return self._modify_file(path, file_spec)
            elif file_spec.action == "delete":
                return self._delete_file(path, file_spec)
            else:
                return FileResult(
                    path=file_spec.path,
                    action=file_spec.action,
                    success=False,
                    error=f"Unknown action: {file_spec.action}"
                )
        except Exception as e:
            return FileResult(
                path=file_spec.path,
                action=file_spec.action,
                success=False,
                error=str(e)
            )
    
    def _create_file(self, path: Path, file_spec: FileSpec) -> FileResult:
        """Create a new file."""
        # Store rollback data if file exists
        if path.exists() and self.enable_rollback:
            self._rollback_data["files_modified"][str(path)] = path.read_text()
        elif self.enable_rollback:
            self._rollback_data["files_created"].append(str(path))
        
        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content
        content = file_spec.content or ""
        path.write_text(content)
        
        return FileResult(
            path=file_spec.path,
            action="create",
            success=True,
            bytes_written=len(content)
        )
    
    def _modify_file(self, path: Path, file_spec: FileSpec) -> FileResult:
        """Modify an existing file."""
        if not path.exists():
            return FileResult(
                path=file_spec.path,
                action="modify",
                success=False,
                error="File does not exist"
            )
        
        # Store original for rollback
        if self.enable_rollback:
            self._rollback_data["files_modified"][str(path)] = path.read_text()
        
        # Write new content
        content = file_spec.content or ""
        path.write_text(content)
        
        return FileResult(
            path=file_spec.path,
            action="modify",
            success=True,
            bytes_written=len(content)
        )
    
    def _delete_file(self, path: Path, file_spec: FileSpec) -> FileResult:
        """Delete a file."""
        if not path.exists():
            return FileResult(
                path=file_spec.path,
                action="delete",
                success=True  # Already doesn't exist
            )
        
        # Store for rollback
        if self.enable_rollback:
            self._rollback_data["files_modified"][str(path)] = path.read_text()
        
        path.unlink()
        
        return FileResult(
            path=file_spec.path,
            action="delete",
            success=True
        )
    
    def _execute_command(self, cmd: ShellCommand) -> CommandResult:
        """Execute a shell command."""
        if self.dry_run:
            return CommandResult(
                command=cmd.command,
                success=True,
                exit_code=0,
                stdout="[dry run]"
            )
        
        start = time.time()
        working_dir = cmd.working_dir or str(self.project_root)
        
        try:
            result = subprocess.run(
                cmd.command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=cmd.timeout_seconds
            )
            
            return CommandResult(
                command=cmd.command,
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=(time.time() - start) * 1000
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                command=cmd.command,
                success=False,
                exit_code=-1,
                stderr=f"Command timed out after {cmd.timeout_seconds}s",
                duration_ms=(time.time() - start) * 1000
            )
        except Exception as e:
            return CommandResult(
                command=cmd.command,
                success=False,
                exit_code=-1,
                stderr=str(e),
                duration_ms=(time.time() - start) * 1000
            )
    
    def _validate_build(
        self,
        blueprint: ProjectBlueprint,
        file_results: List[FileResult]
    ) -> ValidationResult:
        """Validate the completed build."""
        checks = []
        
        # Check 1: All files created successfully
        files_ok = all(fr.success for fr in file_results)
        checks.append(ValidationCheck(
            check_name="files_created",
            check_type="build",
            passed=files_ok,
            confidence_contribution=0.3 if files_ok else 0.0,
            details=f"{sum(1 for fr in file_results if fr.success)}/{len(file_results)} files created"
        ))
        
        # Check 2: Python syntax (for .py files)
        for fr in file_results:
            if fr.path.endswith(".py") and fr.success:
                syntax_ok = self._check_python_syntax(self.project_root / fr.path)
                checks.append(ValidationCheck(
                    check_name=f"syntax:{fr.path}",
                    check_type="build",
                    passed=syntax_ok,
                    confidence_contribution=0.2 if syntax_ok else 0.0,
                    details=f"Python syntax {'valid' if syntax_ok else 'invalid'}"
                ))
        
        # Check 3: Files exist on disk
        for fr in file_results:
            if fr.action != "delete":
                exists = (self.project_root / fr.path).exists()
                checks.append(ValidationCheck(
                    check_name=f"exists:{fr.path}",
                    check_type="build",
                    passed=exists,
                    confidence_contribution=0.1 if exists else 0.0,
                    details=f"File {'exists' if exists else 'missing'}"
                ))
        
        # Calculate overall confidence
        passed_checks = sum(1 for c in checks if c.passed)
        total_checks = len(checks)
        confidence = passed_checks / total_checks if total_checks > 0 else 0.0
        
        return ValidationResult(
            valid=all(c.passed for c in checks if c.check_type == "build"),
            confidence=confidence,
            checks=checks,
            domain="build"
        )
    
    def _check_python_syntax(self, path: Path) -> bool:
        """Check Python file for syntax errors."""
        if not path.exists():
            return False
        
        try:
            code = path.read_text()
            compile(code, str(path), "exec")
            return True
        except SyntaxError:
            return False
    
    def _validation_failed(self, message: str) -> ValidationResult:
        """Create a failed validation result."""
        return ValidationResult(
            valid=False,
            confidence=0.0,
            checks=[ValidationCheck(
                check_name="execution",
                check_type="build",
                passed=False,
                confidence_contribution=0.0,
                details=message
            )],
            domain="build"
        )
    
    def _rollback(self):
        """Rollback changes made during this build."""
        if not self._rollback_data:
            return
        
        # Delete created files
        for path_str in self._rollback_data.get("files_created", []):
            path = Path(path_str)
            if path.exists():
                path.unlink()
        
        # Restore modified files
        for path_str, original_content in self._rollback_data.get("files_modified", {}).items():
            path = Path(path_str)
            path.write_text(original_content)
        
        self._rollback_data = {}
    
    def get_rollback_data(self) -> Optional[Dict[str, Any]]:
        """Get rollback data for this execution."""
        return self._rollback_data if self._rollback_data else None


