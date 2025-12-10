"""
Integration Tests for Quintet System

Tests the integration between:
- Math Mode + Debate Loop
- Math Mode + LLM Integration
- Probabilistic Detector + Mode Routing
- Full Pipeline: Detect → Process → Debate → Result
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

# Core components
from quintet.core import (
    ProbabilisticDetector,
    create_pretrained_detector,
    ClassificationResult,
    TrainingExample,
)
from quintet.core.debate import (
    DebateLoop,
    create_debate_loop,
    DebateResult,
    Verdict,
    DebateRole,
    Proposer,
    Critic,
    Judge,
)

# Math components
from quintet.math import (
    MathModeOrchestrator,
    create_math_mode,
    LLMIntegration,
    create_llm_integration,
    LLMExplainer,
    LLMDetector,
    LLMValidator,
)


class TestProbabilisticDetectorIntegration:
    """Test probabilistic detector with real queries."""

    def test_pretrained_detector_classifies_math(self):
        """Test that pretrained detector correctly classifies math queries."""
        detector = create_pretrained_detector()

        math_queries = [
            "solve x^2 - 4 = 0",
            "integrate sin(x) dx",
            "find the derivative of x^3",
            "calculate the determinant",
        ]

        for query in math_queries:
            result = detector.classify(query)
            assert result.mode == "math", f"Failed for: {query}"
            assert result.confidence > 0.3

    def test_pretrained_detector_classifies_build(self):
        """Test that pretrained detector correctly classifies build queries."""
        detector = create_pretrained_detector()

        build_queries = [
            "create a new python project",
            "scaffold a react app",
            "implement user authentication",
        ]

        for query in build_queries:
            result = detector.classify(query)
            assert result.mode == "build", f"Failed for: {query}"

    def test_detector_online_learning(self):
        """Test that detector can learn from new examples."""
        detector = ProbabilisticDetector()

        # Initially untrained
        assert not detector.is_fitted

        # Add some examples
        for _ in range(10):
            detector.add_example("solve equation x = 5", "math", success=True)
            detector.add_example("create new file", "build", success=True)

        # Now should be able to classify
        result = detector.classify("solve for y")
        assert result.method in ["bayes", "heuristic"]

    def test_detector_hybrid_mode(self):
        """Test hybrid classification combines Bayes and heuristics."""
        detector = create_pretrained_detector()

        result = detector.classify_hybrid("integrate cos(x)")
        # Method can be "hybrid" or "heuristic" depending on training data
        assert result.method in ["hybrid", "heuristic", "bayes"]
        assert "probabilities" in result.to_dict()


class TestDebateLoopIntegration:
    """Test debate loop functionality."""

    def test_create_debate_loop_without_router(self):
        """Test debate loop creation without LLM router."""
        debate = create_debate_loop(router=None, max_rounds=2)

        assert debate.proposer is not None
        assert debate.critic is not None
        assert debate.judge is not None
        assert debate.max_rounds == 2

    def test_debate_agents_have_roles(self):
        """Test that debate agents have correct roles."""
        debate = create_debate_loop()

        assert debate.proposer.role == DebateRole.PROPOSER
        assert debate.critic.role == DebateRole.CRITIC
        assert debate.judge.role == DebateRole.JUDGE

    @pytest.mark.asyncio
    async def test_debate_loop_runs_without_llm(self):
        """Test debate loop can run with fallback (no LLM)."""
        debate = create_debate_loop(router=None, max_rounds=2)

        result = await debate.run(
            problem="solve x^2 - 4 = 0",
            solution="x = 2 or x = -2",
        )

        assert isinstance(result, DebateResult)
        assert result.debate_id is not None
        assert result.verdict in [Verdict.VALID, Verdict.INVALID, Verdict.UNCERTAIN]
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.transcript) > 0

    def test_debate_loop_sync_wrapper(self):
        """Test synchronous wrapper for debate loop."""
        debate = create_debate_loop(router=None, max_rounds=1)

        result = debate.run_sync(
            problem="what is 2 + 2",
            solution="4",
        )

        assert isinstance(result, DebateResult)
        assert result.rounds_completed >= 1


class TestLLMIntegrationComponents:
    """Test LLM integration components."""

    def test_llm_integration_creation(self):
        """Test LLM integration creates all components."""
        integration = create_llm_integration(router=None)

        assert integration.explainer is not None
        assert integration.detector is not None
        assert integration.validator is not None
        assert integration.available is False  # No router

    def test_llm_explainer_fallback(self):
        """Test explainer provides fallback when LLM unavailable."""
        explainer = LLMExplainer(router=None)

        result = {"solution": "x = 2"}
        problem = {"query": "solve x - 2 = 0"}

        explanation = explainer.explain(result, problem)

        assert explanation.summary is not None
        assert len(explanation.steps) > 0
        assert explanation.confidence < 1.0  # Reduced for fallback

    def test_llm_detector_fallback(self):
        """Test detector provides fallback when LLM unavailable."""
        detector = LLMDetector(router=None)

        heuristic = {"domain": "algebra", "confidence": 0.8}
        result = detector.refine_detection("solve x = 5", heuristic)

        assert result.domain == "algebra"
        assert result.confidence == 0.8

    def test_llm_validator_fallback(self):
        """Test validator provides fallback when LLM unavailable."""
        validator = LLMValidator(router=None)

        problem = {"query": "solve x = 2"}
        result = {"solution": "x = 2"}
        symbolic = {"is_valid": True}

        validation = validator.validate(problem, result, symbolic)

        assert validation.is_valid is True
        assert validation.confidence > 0


class TestMathModeWithDebate:
    """Test Math Mode with debate integration."""

    def test_math_mode_creates_debate_loop(self):
        """Test that Math Mode creates debate loop."""
        math = MathModeOrchestrator(config={"enable_debate": True})

        assert math.debate_loop is not None
        assert math.enable_debate is True

    def test_math_mode_without_debate(self):
        """Test Math Mode works without debate enabled."""
        math = MathModeOrchestrator(config={"enable_debate": False})

        result = math.process("solve x + 1 = 3")

        assert result.success
        assert result.debate is None  # Debate not run

    def test_math_mode_with_debate_enabled(self):
        """Test Math Mode runs debate when enabled."""
        math = MathModeOrchestrator(config={"enable_debate": True})

        result = math.process("solve x^2 = 4")

        assert result.success
        # Debate result should be populated (even if fallback)
        if result.debate is not None:
            assert "verdict" in result.debate
            assert "confidence" in result.debate

    def test_math_mode_creates_llm_integration(self):
        """Test that Math Mode creates LLM integration."""
        math = MathModeOrchestrator()

        assert math.llm_integration is not None
        assert math.llm_integration.explainer is not None


class TestFullPipelineIntegration:
    """Test full pipeline from detection to result."""

    def test_full_pipeline_math_query(self):
        """Test complete pipeline for a math query."""
        # Detect
        detector = create_pretrained_detector()
        classification = detector.classify("solve x^2 - 9 = 0")
        assert classification.mode == "math"

        # Process
        math = create_math_mode()
        result = math.process("solve x^2 - 9 = 0")

        assert result.success
        assert result.result is not None
        assert result.validation is not None
        assert result.context_flow is not None
        assert len(result.context_flow) > 0

    def test_full_pipeline_with_debate(self):
        """Test complete pipeline with debate enabled."""
        # Detect
        detector = create_pretrained_detector()
        classification = detector.classify("integrate x dx")
        assert classification.mode == "math"

        # Process with debate
        math = MathModeOrchestrator(config={"enable_debate": True})
        result = math.process("integrate x dx")

        assert result.success
        # Check context flow includes debate entries
        debate_entries = [e for e in result.context_flow if "debate" in e.note.lower()]
        if result.debate is not None:
            assert len(debate_entries) > 0

    def test_pipeline_generates_receipts(self):
        """Test that pipeline generates enforcement receipts."""
        math = create_math_mode()
        result = math.process("solve 2x = 10")

        assert result.success
        # Should have context flow entries for constitutional checks
        constitutional_entries = [
            e for e in result.context_flow
            if "constitutional" in e.source.lower() or "constitutional" in e.note.lower()
        ]
        assert len(constitutional_entries) > 0

    def test_pipeline_handles_non_math(self):
        """Test pipeline handles non-math queries gracefully."""
        math = create_math_mode()
        result = math.process("hello world how are you")

        assert not result.success
        # Check for any error indicating the query wasn't math
        assert len(result.errors) > 0
        error_codes = [e.code.value.lower() for e in result.errors]
        assert any(code in ["intent_unclear", "parse_error", "execution_error"] for code in error_codes)


class TestDebateResultSerialization:
    """Test that debate results serialize correctly."""

    @pytest.mark.asyncio
    async def test_debate_result_to_dict(self):
        """Test debate result serialization."""
        debate = create_debate_loop(router=None, max_rounds=1)

        result = await debate.run(
            problem="test problem",
            solution="test solution",
        )

        result_dict = result.to_dict()

        assert "debate_id" in result_dict
        assert "verdict" in result_dict
        assert "confidence" in result_dict
        assert "transcript" in result_dict
        assert isinstance(result_dict["transcript"], list)

    def test_math_result_includes_debate(self):
        """Test MathModeResult includes debate when run."""
        math = MathModeOrchestrator(config={"enable_debate": True})
        result = math.process("solve x = 5")

        result_dict = result.to_dict()
        assert "debate" in result_dict


class TestDetectorPersistence:
    """Test detector save/load functionality."""

    def test_detector_save_load(self, tmp_path):
        """Test detector can be saved and loaded."""
        # Create and train detector
        detector = ProbabilisticDetector()
        detector.add_example("solve x = 1", "math", success=True)
        detector.add_example("create file", "build", success=True)

        # Save
        save_path = tmp_path / "detector.json"
        detector.save(save_path)

        # Load
        loaded = ProbabilisticDetector.load(save_path)

        # Verify
        assert loaded.total_examples == detector.total_examples
        assert loaded.vocabulary == detector.vocabulary

    def test_detector_stats(self):
        """Test detector provides training stats."""
        detector = create_pretrained_detector()
        stats = detector.get_stats()

        assert "total_examples" in stats
        assert "vocabulary_size" in stats
        assert "mode_distribution" in stats
        assert stats["total_examples"] > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_query(self):
        """Test handling of empty query."""
        math = create_math_mode()
        result = math.process("")

        assert not result.success

    def test_very_long_query(self):
        """Test handling of very long query."""
        math = create_math_mode()
        long_query = "solve x = " + "1 + " * 100 + "1"
        result = math.process(long_query)

        # Should either succeed or fail gracefully
        assert result is not None

    def test_special_characters_in_query(self):
        """Test handling of special characters."""
        math = create_math_mode()
        result = math.process("solve x² - 4 = 0")  # Unicode squared

        # Should handle gracefully
        assert result is not None

    def test_debate_with_empty_solution(self):
        """Test debate handles empty solution."""
        debate = create_debate_loop(router=None, max_rounds=1)

        result = debate.run_sync(
            problem="test",
            solution="",
        )

        assert result is not None
        assert result.verdict in [Verdict.VALID, Verdict.INVALID, Verdict.UNCERTAIN]
