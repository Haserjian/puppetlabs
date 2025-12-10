"""
Math Backend Base Class
========================

Abstract base for all math computation backends.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass


@dataclass
class BackendResult:
    """Result from a backend computation."""
    success: bool
    output: Any
    output_latex: Optional[str] = None
    method_used: str = ""
    execution_time_ms: float = 0.0
    logs: List[str] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.logs is None:
            self.logs = []
        if self.errors is None:
            self.errors = []


class MathBackend(ABC):
    """
    Abstract base class for math computation backends.
    
    All backends must implement:
    - name: Backend identifier
    - is_available: Check if backend can run
    - capabilities: What operations this backend supports
    - execute: Run a computation
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Backend identifier (e.g., 'sympy', 'numpy')."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend's dependencies are installed."""
        pass
    
    @property
    @abstractmethod
    def capabilities(self) -> List[str]:
        """
        List of capabilities this backend supports.
        
        Examples: 'symbolic', 'numeric', 'solve', 'integrate', 
                  'differentiate', 'matrix', 'optimize', etc.
        """
        pass
    
    @abstractmethod
    def execute(
        self,
        operation: str,
        inputs: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> BackendResult:
        """
        Execute a computation.
        
        Args:
            operation: What to do ('solve', 'integrate', 'simplify', etc.)
            inputs: Input data (expressions, variables, constraints)
            options: Optional configuration
            
        Returns:
            BackendResult with output and metadata
        """
        pass
    
    def supports(self, operation: str) -> bool:
        """Check if this backend supports an operation."""
        return operation in self.capabilities


