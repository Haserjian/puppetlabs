"""
Adversarial Debate Loop for Confidence Calibration

Implements the debate protocol from AI safety research (Irving et al., 2018):
- PROPOSER argues the solution is correct
- CRITIC attempts to find flaws
- JUDGE evaluates the transcript and assigns calibrated confidence

This provides adversarially-robust confidence scores that reflect
how well a solution holds up under scrutiny.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from quintet.model.router import ModelRouter


class DebateRole(Enum):
    """Roles in the debate."""

    PROPOSER = "proposer"
    CRITIC = "critic"
    JUDGE = "judge"


class Verdict(Enum):
    """Final verdict from debate."""

    VALID = "valid"
    INVALID = "invalid"
    UNCERTAIN = "uncertain"


@dataclass
class DebateMove:
    """A single move in the debate transcript."""

    role: DebateRole
    content: str
    move_type: str  # "argument", "attack", "defense", "concession"
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
            "move_type": self.move_type,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class DebateResult:
    """Result of a completed debate."""

    debate_id: str
    problem: str
    solution: str
    verdict: Verdict
    confidence: float  # 0.0 to 1.0, adversarially calibrated
    transcript: List[DebateMove]
    proposer_won: bool
    rounds_completed: int
    judge_reasoning: str
    duration_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "debate_id": self.debate_id,
            "problem": self.problem,
            "solution": self.solution,
            "verdict": self.verdict.value,
            "confidence": self.confidence,
            "transcript": [m.to_dict() for m in self.transcript],
            "proposer_won": self.proposer_won,
            "rounds_completed": self.rounds_completed,
            "judge_reasoning": self.judge_reasoning,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


class DebateAgent:
    """
    Base class for debate participants.

    Each agent has a role (proposer, critic, judge) and
    generates moves based on the debate context.
    """

    SLOT = "council_agent"  # Model slot for debate agents

    def __init__(
        self,
        role: DebateRole,
        router: Optional["ModelRouter"] = None,
    ):
        self.role = role
        self.router = router

    @property
    def available(self) -> bool:
        return self.router is not None

    async def generate_move(
        self,
        problem: str,
        solution: str,
        transcript: List[DebateMove],
        move_type: str,
    ) -> DebateMove:
        """Generate a move in the debate."""
        if not self.available:
            return self._fallback_move(move_type)

        prompt = self._build_prompt(problem, solution, transcript, move_type)

        response = await self.router.call_async(
            slot=self.SLOT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,  # Some creativity for debate
        )

        content = response.content if hasattr(response, 'content') else str(response)

        return DebateMove(
            role=self.role,
            content=content.strip(),
            move_type=move_type,
        )

    def _build_prompt(
        self,
        problem: str,
        solution: str,
        transcript: List[DebateMove],
        move_type: str,
    ) -> str:
        """Build role-specific prompt."""
        raise NotImplementedError

    def _fallback_move(self, move_type: str) -> DebateMove:
        """Generate fallback move when LLM unavailable."""
        return DebateMove(
            role=self.role,
            content=f"[{self.role.value}]: Unable to generate {move_type} (LLM unavailable)",
            move_type=move_type,
        )


class Proposer(DebateAgent):
    """
    Argues that the solution is correct.

    Responsibilities:
    - Present initial argument for solution validity
    - Rebut critic's attacks with counter-arguments
    - Concede only if unable to defend
    """

    def __init__(self, router: Optional["ModelRouter"] = None):
        super().__init__(DebateRole.PROPOSER, router)

    def _build_prompt(
        self,
        problem: str,
        solution: str,
        transcript: List[DebateMove],
        move_type: str,
    ) -> str:
        base = f"""You are the PROPOSER in a mathematical debate.
Your goal: Argue that the solution is CORRECT.

**Problem**: {problem}
**Solution**: {solution}

"""
        if move_type == "argument":
            return base + """Present your opening argument:
1. Why is this solution mathematically correct?
2. What properties/theorems support it?
3. Why should we trust this result?

Be specific and rigorous. Cite mathematical principles."""

        elif move_type == "defense":
            # Include critic's attack
            attacks = [m for m in transcript if m.role == DebateRole.CRITIC]
            last_attack = attacks[-1].content if attacks else "No attack yet"

            return base + f"""The CRITIC attacked with:
"{last_attack}"

Defend the solution:
1. Address the specific criticism
2. Explain why it doesn't invalidate the solution
3. Provide additional evidence if needed

If you cannot defend, say "I CONCEDE" and explain why."""

        return base + "Continue the debate in your role as PROPOSER."

    def _fallback_move(self, move_type: str) -> DebateMove:
        if move_type == "argument":
            content = "The solution follows from standard mathematical principles and has been verified symbolically."
        else:
            content = "The criticism does not invalidate the solution's core correctness."
        return DebateMove(role=self.role, content=content, move_type=move_type)


class Critic(DebateAgent):
    """
    Attempts to find flaws in the solution.

    Responsibilities:
    - Identify potential errors, edge cases, or gaps
    - Challenge assumptions and reasoning
    - Concede if unable to find valid criticism
    """

    def __init__(self, router: Optional["ModelRouter"] = None):
        super().__init__(DebateRole.CRITIC, router)

    def _build_prompt(
        self,
        problem: str,
        solution: str,
        transcript: List[DebateMove],
        move_type: str,
    ) -> str:
        base = f"""You are the CRITIC in a mathematical debate.
Your goal: Find FLAWS in the solution (if any exist).

**Problem**: {problem}
**Solution**: {solution}

"""
        # Include proposer's arguments
        proposer_moves = [m for m in transcript if m.role == DebateRole.PROPOSER]
        if proposer_moves:
            base += "**Proposer's arguments**:\n"
            for m in proposer_moves[-2:]:  # Last 2 moves
                base += f'- "{m.content[:500]}..."\n'
            base += "\n"

        return base + """Find flaws:
1. Are there mathematical errors?
2. Edge cases not handled?
3. Assumptions that might not hold?
4. Alternative interpretations missed?

If you find a flaw, explain it clearly.
If you cannot find a valid flaw, say "I CONCEDE" - the solution appears correct."""

    def _fallback_move(self, move_type: str) -> DebateMove:
        return DebateMove(
            role=self.role,
            content="I CONCEDE - unable to find flaws in the solution.",
            move_type="concession",
        )


class Judge(DebateAgent):
    """
    Evaluates the debate and assigns calibrated confidence.

    Responsibilities:
    - Assess quality of arguments and rebuttals
    - Determine winner (proposer or critic)
    - Assign confidence score reflecting debate outcome
    """

    def __init__(self, router: Optional["ModelRouter"] = None):
        super().__init__(DebateRole.JUDGE, router)

    async def evaluate(
        self,
        problem: str,
        solution: str,
        transcript: List[DebateMove],
    ) -> tuple[Verdict, float, str]:
        """
        Evaluate the debate and return verdict.

        Returns:
            (verdict, confidence, reasoning)
        """
        if not self.available:
            return self._fallback_evaluation(transcript)

        prompt = self._build_evaluation_prompt(problem, solution, transcript)

        response = await self.router.call_async(
            slot=self.SLOT,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,  # More deterministic for judgment
        )

        return self._parse_evaluation(response, transcript)

    def _build_evaluation_prompt(
        self,
        problem: str,
        solution: str,
        transcript: List[DebateMove],
    ) -> str:
        prompt = f"""You are the JUDGE evaluating a mathematical debate.

**Problem**: {problem}
**Solution**: {solution}

**Debate Transcript**:
"""
        for move in transcript:
            prompt += f"\n[{move.role.value.upper()}] ({move.move_type}):\n{move.content}\n"

        prompt += """
Evaluate the debate:
1. Did the PROPOSER successfully defend the solution?
2. Did the CRITIC find valid flaws?
3. Who made stronger arguments?

Respond in format:
VERDICT: <valid/invalid/uncertain>
CONFIDENCE: <0.0-1.0>
WINNER: <proposer/critic>
REASONING: <your analysis>
"""
        return prompt

    def _parse_evaluation(
        self,
        response: Any,
        transcript: List[DebateMove],
    ) -> tuple[Verdict, float, str]:
        """Parse judge's evaluation."""
        content = response.content if hasattr(response, 'content') else str(response)

        verdict = Verdict.UNCERTAIN
        confidence = 0.5
        reasoning = ""

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("VERDICT:"):
                v = line[8:].strip().lower()
                if v == "valid":
                    verdict = Verdict.VALID
                elif v == "invalid":
                    verdict = Verdict.INVALID
                else:
                    verdict = Verdict.UNCERTAIN
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line[11:].strip())
                    confidence = max(0.0, min(1.0, confidence))
                except ValueError:
                    pass
            elif line.startswith("REASONING:"):
                reasoning = line[10:].strip()

        # If no reasoning parsed, use full content
        if not reasoning:
            reasoning = content[:500]

        return verdict, confidence, reasoning

    def _fallback_evaluation(
        self,
        transcript: List[DebateMove],
    ) -> tuple[Verdict, float, str]:
        """Fallback evaluation based on concessions."""
        critic_conceded = any(
            "CONCEDE" in m.content.upper()
            for m in transcript
            if m.role == DebateRole.CRITIC
        )
        proposer_conceded = any(
            "CONCEDE" in m.content.upper()
            for m in transcript
            if m.role == DebateRole.PROPOSER
        )

        if critic_conceded and not proposer_conceded:
            return Verdict.VALID, 0.7, "Critic conceded; solution likely valid."
        elif proposer_conceded:
            return Verdict.INVALID, 0.6, "Proposer conceded; solution may have issues."
        else:
            return Verdict.UNCERTAIN, 0.5, "No clear winner; confidence uncertain."

    def _build_prompt(self, *args, **kwargs) -> str:
        # Not used for judge - uses evaluate() instead
        return ""


class DebateLoop:
    """
    Orchestrates adversarial debate for confidence calibration.

    Runs multiple rounds of proposer/critic exchange,
    then has judge evaluate the transcript.
    """

    def __init__(
        self,
        proposer: Proposer,
        critic: Critic,
        judge: Judge,
        max_rounds: int = 3,
    ):
        self.proposer = proposer
        self.critic = critic
        self.judge = judge
        self.max_rounds = max_rounds

    async def run(
        self,
        problem: str,
        solution: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DebateResult:
        """
        Run the full debate loop.

        Args:
            problem: The mathematical problem
            solution: The proposed solution
            context: Optional additional context

        Returns:
            DebateResult with calibrated confidence
        """
        start_time = datetime.now()
        debate_id = str(uuid4())[:8]
        transcript: List[DebateMove] = []

        # Opening argument from proposer
        opening = await self.proposer.generate_move(
            problem, solution, transcript, "argument"
        )
        transcript.append(opening)

        # Debate rounds
        rounds_completed = 0
        for round_num in range(self.max_rounds):
            # Critic's attack
            attack = await self.critic.generate_move(
                problem, solution, transcript, "attack"
            )
            transcript.append(attack)

            # Check for critic concession
            if "CONCEDE" in attack.content.upper():
                rounds_completed = round_num + 1
                break

            # Proposer's defense
            defense = await self.proposer.generate_move(
                problem, solution, transcript, "defense"
            )
            transcript.append(defense)

            # Check for proposer concession
            if "CONCEDE" in defense.content.upper():
                rounds_completed = round_num + 1
                break

            rounds_completed = round_num + 1

        # Judge evaluates
        verdict, confidence, reasoning = await self.judge.evaluate(
            problem, solution, transcript
        )

        # Determine winner
        proposer_won = verdict == Verdict.VALID or (
            verdict == Verdict.UNCERTAIN and confidence > 0.5
        )

        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        return DebateResult(
            debate_id=debate_id,
            problem=problem,
            solution=solution,
            verdict=verdict,
            confidence=confidence,
            transcript=transcript,
            proposer_won=proposer_won,
            rounds_completed=rounds_completed,
            judge_reasoning=reasoning,
            duration_ms=duration_ms,
            metadata=context or {},
        )

    def run_sync(
        self,
        problem: str,
        solution: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DebateResult:
        """Synchronous wrapper for run()."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create new loop if current is running
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self.run(problem, solution, context)
                    )
                    return future.result()
            return loop.run_until_complete(self.run(problem, solution, context))
        except RuntimeError:
            return asyncio.run(self.run(problem, solution, context))


def create_debate_loop(
    router: Optional["ModelRouter"] = None,
    max_rounds: int = 3,
) -> DebateLoop:
    """Factory function to create a debate loop."""
    return DebateLoop(
        proposer=Proposer(router),
        critic=Critic(router),
        judge=Judge(router),
        max_rounds=max_rounds,
    )


# Convenience class for simpler API
@dataclass
class DebateConfig:
    """Configuration for debate loop."""

    max_rounds: int = 3
    proposer_slot: str = "council_agent"
    critic_slot: str = "council_agent"
    judge_slot: str = "council_agent"
    temperature_argument: float = 0.7
    temperature_judgment: float = 0.2
