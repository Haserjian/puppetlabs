"""
Probabilistic Domain Detector

Bayesian classifier for mathematical domain detection that:
- Learns from episode history (weak supervision)
- Falls back to keyword heuristics when untrained
- Supports online learning (add examples incrementally)
- Provides calibrated confidence scores

This replaces brittle keyword matching with learned classification.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import math


@dataclass
class ClassificationResult:
    """Result of probabilistic classification."""

    mode: str  # Primary mode (math, build, chemistry, biology, unknown)
    confidence: float  # 0.0 to 1.0
    probabilities: Dict[str, float]  # P(mode) for all modes
    method: str  # "bayes", "heuristic", or "hybrid"
    features_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "confidence": self.confidence,
            "probabilities": self.probabilities,
            "method": self.method,
            "features_used": self.features_used,
        }


@dataclass
class TrainingExample:
    """A single training example."""

    query: str
    mode: str
    success: bool = True
    weight: float = 1.0


class ProbabilisticDetector:
    """
    Bayesian classifier for domain detection.

    Uses Naive Bayes with TF-IDF-like features for
    text classification into mathematical domains.
    """

    # Supported modes
    MODES = ["math", "build", "chemistry", "biology", "unknown"]

    # Heuristic keywords per mode (fallback)
    KEYWORDS: Dict[str, Set[str]] = {
        "math": {
            "solve", "equation", "integrate", "derivative", "matrix",
            "vector", "calculate", "compute", "simplify", "factor",
            "polynomial", "quadratic", "linear", "algebra", "calculus",
            "limit", "sum", "product", "series", "sequence", "proof",
            "theorem", "formula", "expression", "variable", "function",
            "graph", "plot", "root", "zero", "solution", "eigenvalue",
            "determinant", "inverse", "transpose", "gradient", "hessian",
            "integral", "differentiate", "taylor", "fourier", "laplace",
        },
        "build": {
            "create", "build", "generate", "scaffold", "implement",
            "refactor", "test", "fix", "debug", "deploy", "setup",
            "configure", "install", "project", "file", "folder",
            "directory", "code", "script", "function", "class",
            "module", "package", "api", "endpoint", "server",
        },
        "chemistry": {
            "molecule", "compound", "reaction", "element", "atom",
            "bond", "orbital", "electron", "proton", "neutron",
            "acid", "base", "ph", "molar", "concentration", "solution",
            "precipitate", "catalyst", "enzyme", "protein", "synthesis",
        },
        "biology": {
            "cell", "gene", "dna", "rna", "protein", "enzyme",
            "organism", "species", "evolution", "mutation", "genome",
            "chromosome", "mitosis", "meiosis", "photosynthesis",
            "respiration", "metabolism", "anatomy", "physiology",
        },
    }

    def __init__(self):
        # Prior probabilities P(mode)
        self.mode_counts: Counter = Counter()
        self.total_examples: int = 0

        # Likelihood P(word|mode)
        self.word_counts: Dict[str, Counter] = defaultdict(Counter)
        self.mode_word_totals: Counter = Counter()

        # Vocabulary
        self.vocabulary: Set[str] = set()

        # Smoothing parameter (Laplace)
        self.alpha: float = 1.0

        # Whether we have enough data
        self.min_examples_per_mode: int = 5
        self._fitted: bool = False

    @property
    def is_fitted(self) -> bool:
        """Check if classifier has been trained."""
        return self._fitted and self.total_examples >= self.min_examples_per_mode

    def fit(self, examples: List[TrainingExample]) -> "ProbabilisticDetector":
        """
        Train the classifier on examples.

        Args:
            examples: List of (query, mode, success) training examples

        Returns:
            self for chaining
        """
        # Reset counts
        self.mode_counts = Counter()
        self.word_counts = defaultdict(Counter)
        self.mode_word_totals = Counter()
        self.vocabulary = set()
        self.total_examples = 0

        for example in examples:
            self.add_example(
                example.query,
                example.mode,
                example.success,
                example.weight,
            )

        self._fitted = True
        return self

    def add_example(
        self,
        query: str,
        mode: str,
        success: bool = True,
        weight: float = 1.0,
    ) -> None:
        """
        Add a single training example (online learning).

        Args:
            query: The query text
            mode: The correct mode label
            success: Whether the classification led to success
            weight: Weight for this example (default 1.0)
        """
        if mode not in self.MODES:
            mode = "unknown"

        # Weight by success (successful classifications are better labels)
        effective_weight = weight * (1.0 if success else 0.5)

        # Tokenize
        words = self._tokenize(query)

        # Update counts
        self.mode_counts[mode] += effective_weight
        self.total_examples += effective_weight

        for word in words:
            self.word_counts[mode][word] += effective_weight
            self.mode_word_totals[mode] += effective_weight
            self.vocabulary.add(word)

    def classify(self, query: str) -> ClassificationResult:
        """
        Classify a query into a mode.

        Uses Bayesian classification if trained, otherwise
        falls back to keyword heuristics.

        Args:
            query: The query to classify

        Returns:
            ClassificationResult with mode and confidence
        """
        if self.is_fitted:
            return self._classify_bayes(query)
        else:
            return self._classify_heuristic(query)

    def classify_hybrid(self, query: str) -> ClassificationResult:
        """
        Hybrid classification combining Bayes and heuristics.

        Useful when Bayesian model is weak or uncertain.
        """
        bayes_result = self._classify_bayes(query) if self.is_fitted else None
        heuristic_result = self._classify_heuristic(query)

        if bayes_result is None:
            return heuristic_result

        # Combine probabilities (weighted average)
        bayes_weight = min(self.total_examples / 100, 0.8)  # More data = more trust
        heuristic_weight = 1.0 - bayes_weight

        combined_probs = {}
        all_modes = set(bayes_result.probabilities.keys()) | set(heuristic_result.probabilities.keys())

        for mode in all_modes:
            bayes_prob = bayes_result.probabilities.get(mode, 0.0)
            heuristic_prob = heuristic_result.probabilities.get(mode, 0.0)
            combined_probs[mode] = bayes_weight * bayes_prob + heuristic_weight * heuristic_prob

        # Normalize
        total = sum(combined_probs.values())
        if total > 0:
            combined_probs = {k: v / total for k, v in combined_probs.items()}

        # Find best mode
        best_mode = max(combined_probs, key=combined_probs.get)
        confidence = combined_probs[best_mode]

        return ClassificationResult(
            mode=best_mode,
            confidence=confidence,
            probabilities=combined_probs,
            method="hybrid",
            features_used=bayes_result.features_used + ["heuristic_keywords"],
        )

    def _classify_bayes(self, query: str) -> ClassificationResult:
        """Bayesian classification using trained model."""
        words = self._tokenize(query)
        vocab_size = len(self.vocabulary) or 1

        log_probs = {}
        features_used = []

        for mode in self.MODES:
            # Log prior: P(mode)
            prior = (self.mode_counts[mode] + self.alpha) / (self.total_examples + self.alpha * len(self.MODES))
            log_prob = math.log(prior)

            # Log likelihood: P(words|mode)
            mode_total = self.mode_word_totals[mode] + self.alpha * vocab_size

            for word in words:
                word_count = self.word_counts[mode][word] + self.alpha
                log_prob += math.log(word_count / mode_total)

                if word in self.vocabulary:
                    features_used.append(word)

            log_probs[mode] = log_prob

        # Convert to probabilities (softmax)
        max_log = max(log_probs.values())
        probs = {mode: math.exp(lp - max_log) for mode, lp in log_probs.items()}
        total = sum(probs.values())
        probs = {mode: p / total for mode, p in probs.items()}

        # Find best
        best_mode = max(probs, key=probs.get)
        confidence = probs[best_mode]

        return ClassificationResult(
            mode=best_mode,
            confidence=confidence,
            probabilities=probs,
            method="bayes",
            features_used=list(set(features_used))[:10],  # Top 10 features
        )

    def _classify_heuristic(self, query: str) -> ClassificationResult:
        """Keyword-based heuristic classification."""
        query_lower = query.lower()
        words = set(self._tokenize(query))

        scores = {}
        features_used = []

        for mode, keywords in self.KEYWORDS.items():
            matches = words & keywords
            scores[mode] = len(matches)
            features_used.extend(matches)

        # Add small score for unknown to handle no-match case
        scores["unknown"] = 0.1

        # Normalize to probabilities
        total = sum(scores.values())
        probs = {mode: score / total for mode, score in scores.items()}

        # Find best
        best_mode = max(probs, key=probs.get)
        confidence = probs[best_mode]

        # Adjust confidence based on match quality
        if scores[best_mode] == 0:
            confidence = 0.2  # Very uncertain
        elif scores[best_mode] < 2:
            confidence = min(confidence, 0.5)  # Somewhat uncertain

        return ClassificationResult(
            mode=best_mode,
            confidence=confidence,
            probabilities=probs,
            method="heuristic",
            features_used=list(set(features_used)),
        )

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Lowercase and extract words
        text = text.lower()
        words = re.findall(r'\b[a-z]+\b', text)

        # Remove very short words
        words = [w for w in words if len(w) > 2]

        return words

    def save(self, path: Path) -> None:
        """Save model to JSON file."""
        data = {
            "mode_counts": dict(self.mode_counts),
            "word_counts": {mode: dict(counts) for mode, counts in self.word_counts.items()},
            "mode_word_totals": dict(self.mode_word_totals),
            "vocabulary": list(self.vocabulary),
            "total_examples": self.total_examples,
            "alpha": self.alpha,
            "fitted": self._fitted,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "ProbabilisticDetector":
        """Load model from JSON file."""
        with open(path) as f:
            data = json.load(f)

        detector = cls()
        detector.mode_counts = Counter(data["mode_counts"])
        detector.word_counts = defaultdict(Counter, {
            mode: Counter(counts) for mode, counts in data["word_counts"].items()
        })
        detector.mode_word_totals = Counter(data["mode_word_totals"])
        detector.vocabulary = set(data["vocabulary"])
        detector.total_examples = data["total_examples"]
        detector.alpha = data.get("alpha", 1.0)
        detector._fitted = data.get("fitted", True)

        return detector

    def get_stats(self) -> Dict[str, Any]:
        """Get training statistics."""
        return {
            "total_examples": self.total_examples,
            "vocabulary_size": len(self.vocabulary),
            "mode_distribution": dict(self.mode_counts),
            "is_fitted": self.is_fitted,
            "min_examples_needed": self.min_examples_per_mode,
        }


def train_detector_from_episodes(
    episodes: List[Dict[str, Any]],
    success_field: str = "success",
    query_field: str = "query",
    mode_field: str = "mode",
) -> ProbabilisticDetector:
    """
    Train a detector from episode history.

    Args:
        episodes: List of episode dicts
        success_field: Field name for success indicator
        query_field: Field name for query text
        mode_field: Field name for mode label

    Returns:
        Trained ProbabilisticDetector
    """
    examples = []

    for episode in episodes:
        query = episode.get(query_field, "")
        mode = episode.get(mode_field, "unknown")
        success = episode.get(success_field, True)

        if query:
            examples.append(TrainingExample(
                query=query,
                mode=mode,
                success=success,
            ))

    detector = ProbabilisticDetector()
    detector.fit(examples)

    return detector


def load_episodes_from_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load episodes from JSONL file."""
    episodes = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                episodes.append(json.loads(line))
    return episodes


# Pre-built detector with common math examples
def create_pretrained_detector() -> ProbabilisticDetector:
    """Create a detector pre-trained on common examples."""
    detector = ProbabilisticDetector()

    # Math examples
    math_examples = [
        "solve x^2 - 4 = 0",
        "integrate sin(x) dx",
        "find the derivative of x^3",
        "calculate the determinant of matrix A",
        "simplify (x+1)^2",
        "factor x^2 - 5x + 6",
        "find eigenvalues of [[1,2],[3,4]]",
        "compute gradient of f(x,y) = x^2 + y^2",
        "solve the system 2x + y = 5, x - y = 1",
        "evaluate the limit of (x^2-1)/(x-1) as x->1",
        "find the taylor series of e^x",
        "compute the fourier transform",
        "what is 2 + 2",
        "calculate 15% of 200",
    ]

    # Build examples
    build_examples = [
        "create a new python project",
        "scaffold a react app",
        "generate a REST API",
        "implement user authentication",
        "refactor the database module",
        "fix the bug in login.py",
        "add tests for the parser",
        "deploy to production",
        "setup docker container",
        "create a CLI tool",
    ]

    # Chemistry examples
    chemistry_examples = [
        "balance the equation H2 + O2 -> H2O",
        "calculate the molar mass of NaCl",
        "what is the pH of 0.1M HCl",
        "draw the lewis structure of CO2",
        "explain sp3 hybridization",
    ]

    # Biology examples
    biology_examples = [
        "explain DNA replication",
        "what is the krebs cycle",
        "describe mitosis phases",
        "how does photosynthesis work",
        "explain protein synthesis",
    ]

    # Train on examples
    for query in math_examples:
        detector.add_example(query, "math", success=True)

    for query in build_examples:
        detector.add_example(query, "build", success=True)

    for query in chemistry_examples:
        detector.add_example(query, "chemistry", success=True)

    for query in biology_examples:
        detector.add_example(query, "biology", success=True)

    return detector
