"""
Edge Case Registry
==================

Extensible registry for domain-specific edge cases with
support for custom edge case generators and categorization.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Callable, Optional
import logging
import functools

logger = logging.getLogger(__name__)


@dataclass
class EdgeCase:
    """Definition of an edge case for stress testing."""

    case_id: str
    domain: str           # "algebra", "calculus", "statistics", etc.
    category: str         # "overflow", "underflow", "singularity", "ill_conditioned"
    description: str
    generator: Optional[Callable[[], Dict[str, Any]]] = None
    expected_behavior: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding generator function)."""
        return {
            "case_id": self.case_id,
            "domain": self.domain,
            "category": self.category,
            "description": self.description,
            "expected_behavior": self.expected_behavior,
            "tags": self.tags,
        }

    def generate(self) -> Dict[str, Any]:
        """Generate edge case data.

        Returns:
            Edge case problem specification
        """
        if self.generator:
            return self.generator()
        return self.expected_behavior


class EdgeCaseRegistry:
    """Thread-safe registry for edge cases."""

    def __init__(self):
        """Initialize registry."""
        self._cases: Dict[str, List[EdgeCase]] = {}
        self._logger = logger

    def register(self, domain: str, case: EdgeCase) -> None:
        """Register an edge case.

        Args:
            domain: Problem domain
            case: EdgeCase instance
        """
        if domain not in self._cases:
            self._cases[domain] = []

        # Check for duplicate
        for existing in self._cases[domain]:
            if existing.case_id == case.case_id:
                self._logger.warning(f"Overwriting edge case: {case.case_id}")
                self._cases[domain].remove(existing)
                break

        self._cases[domain].append(case)
        self._logger.debug(f"Registered edge case: {case.case_id} in domain {domain}")

    def get_cases(
        self,
        domain: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[EdgeCase]:
        """Get edge cases by domain and optional filters.

        Args:
            domain: Problem domain
            category: Optional category filter
            tags: Optional tags filter (match any)

        Returns:
            List of matching EdgeCase objects
        """
        cases = self._cases.get(domain, [])

        if category:
            cases = [c for c in cases if c.category == category]

        if tags:
            cases = [c for c in cases if any(tag in c.tags for tag in tags)]

        return cases

    def list_domains(self) -> List[str]:
        """Get list of registered domains.

        Returns:
            List of domain names
        """
        return list(self._cases.keys())

    def list_categories(self, domain: str) -> List[str]:
        """Get unique categories for a domain.

        Args:
            domain: Problem domain

        Returns:
            List of category names
        """
        cases = self._cases.get(domain, [])
        categories = set(c.category for c in cases)
        return sorted(list(categories))

    def count_cases(self, domain: Optional[str] = None) -> int:
        """Count total edge cases.

        Args:
            domain: Optional domain filter

        Returns:
            Number of edge cases
        """
        if domain:
            return len(self._cases.get(domain, []))
        return sum(len(cases) for cases in self._cases.values())

    def export(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """Export registry data.

        Args:
            domain: Optional domain filter

        Returns:
            Dictionary with case data
        """
        if domain:
            cases = self._cases.get(domain, [])
            return {
                domain: [c.to_dict() for c in cases]
            }

        result = {}
        for d, cases in self._cases.items():
            result[d] = [c.to_dict() for c in cases]

        return result


# Global singleton registry
_registry: Optional[EdgeCaseRegistry] = None


def get_edge_case_registry() -> EdgeCaseRegistry:
    """Get or create global edge case registry.

    Returns:
        EdgeCaseRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = EdgeCaseRegistry()
    return _registry


def register_edge_case(
    domain: str,
    case_id: str,
    category: str,
    description: str,
    tags: Optional[List[str]] = None,
    expected_behavior: Optional[Dict[str, Any]] = None
):
    """Decorator to register an edge case generator function.

    Args:
        domain: Problem domain
        case_id: Unique case identifier
        category: Edge case category
        description: Human-readable description
        tags: Optional tags
        expected_behavior: Optional expected behavior spec

    Returns:
        Decorator function
    """
    def decorator(generator_func: Callable[[], Dict[str, Any]]) -> Callable:
        """Decorator implementation."""
        case = EdgeCase(
            case_id=case_id,
            domain=domain,
            category=category,
            description=description,
            generator=generator_func,
            expected_behavior=expected_behavior or {},
            tags=tags or []
        )

        registry = get_edge_case_registry()
        registry.register(domain, case)

        @functools.wraps(generator_func)
        def wrapper(*args: Any, **kwargs: Any) -> Dict[str, Any]:
            return generator_func(*args, **kwargs)

        return wrapper

    return decorator


# Built-in edge cases for algebra domain

@register_edge_case(
    domain="algebra",
    case_id="overflow_quadratic",
    category="overflow",
    description="Quadratic equation with coefficients near float64 max",
    tags=["quadratic", "numeric_limits"],
    expected_behavior={"outcome": "degraded_success", "confidence_min": 0.4}
)
def generate_overflow_quadratic() -> Dict[str, Any]:
    """Generate overflow edge case."""
    return {
        "type": "solve",
        "problem_type": "solve",
        "domain": "algebra",
        "expressions": ["x^2 - 1e308*x + 1e307 = 0"],
        "variables": ["x"]
    }


@register_edge_case(
    domain="algebra",
    case_id="underflow_quadratic",
    category="underflow",
    description="Quadratic equation with tiny coefficients",
    tags=["quadratic", "numeric_limits"],
    expected_behavior={"outcome": "degraded_success", "confidence_min": 0.4}
)
def generate_underflow_quadratic() -> Dict[str, Any]:
    """Generate underflow edge case."""
    return {
        "type": "solve",
        "problem_type": "solve",
        "domain": "algebra",
        "expressions": ["1e-100*x^2 - 1e-100*x + 1e-101 = 0"],
        "variables": ["x"]
    }


@register_edge_case(
    domain="algebra",
    case_id="ill_conditioned_system",
    category="ill_conditioned",
    description="Nearly singular linear system",
    tags=["system", "conditioning"],
    expected_behavior={"outcome": "degraded_success", "confidence_min": 0.5}
)
def generate_ill_conditioned_system() -> Dict[str, Any]:
    """Generate ill-conditioned system."""
    return {
        "type": "solve",
        "problem_type": "solve",
        "domain": "algebra",
        "expressions": [
            "x + y = 2",
            "1.00000001*x + 0.99999999*y = 2"
        ],
        "variables": ["x", "y"]
    }


@register_edge_case(
    domain="algebra",
    case_id="large_degree_polynomial",
    category="complexity",
    description="High-degree polynomial",
    tags=["polynomial", "complexity"],
    expected_behavior={"outcome": "degraded_success", "confidence_min": 0.3}
)
def generate_large_degree_polynomial() -> Dict[str, Any]:
    """Generate high-degree polynomial."""
    return {
        "type": "solve",
        "problem_type": "solve",
        "domain": "algebra",
        "expressions": ["x^10 - 1 = 0"],
        "variables": ["x"]
    }


@register_edge_case(
    domain="algebra",
    case_id="repeated_roots",
    category="singularity",
    description="Polynomial with repeated roots",
    tags=["polynomial", "roots"],
    expected_behavior={"outcome": "success", "confidence_min": 0.6}
)
def generate_repeated_roots() -> Dict[str, Any]:
    """Generate polynomial with repeated roots."""
    return {
        "type": "solve",
        "problem_type": "solve",
        "domain": "algebra",
        "expressions": ["(x - 1)^3 = 0"],
        "variables": ["x"]
    }


@register_edge_case(
    domain="algebra",
    case_id="complex_roots",
    category="complexity",
    description="Polynomial with complex roots",
    tags=["polynomial", "complex"],
    expected_behavior={"outcome": "success", "confidence_min": 0.7}
)
def generate_complex_roots() -> Dict[str, Any]:
    """Generate polynomial with complex roots."""
    return {
        "type": "solve",
        "problem_type": "solve",
        "domain": "algebra",
        "expressions": ["x^2 + 1 = 0"],
        "variables": ["x"]
    }


@register_edge_case(
    domain="algebra",
    case_id="parametric_solution",
    category="complexity",
    description="Equation with parametric solution",
    tags=["system", "parametric"],
    expected_behavior={"outcome": "success", "confidence_min": 0.5}
)
def generate_parametric_solution() -> Dict[str, Any]:
    """Generate equation with parametric solution."""
    return {
        "type": "solve",
        "problem_type": "solve",
        "domain": "algebra",
        "expressions": ["x + y = 1"],
        "variables": ["x", "y"]
    }
