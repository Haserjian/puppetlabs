"""
Quintet Sandbox CLI
====================

Minimal CLI for tactile experimentation with Math Mode.
Every query you run becomes an Episode row in your JSONL dataset.

Usage:
    python -m quintet.cli "Solve x + y = 5 and 2x - y = 1"
    python -m quintet.cli "Integrate 2*x with respect to x"
    python -m quintet.cli "What is the gradient of x^2 + y^2?"
"""

import argparse
import sys
from datetime import datetime


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Quintet sandbox CLI - run Math Mode queries and log episodes"
    )
    parser.add_argument("query", nargs="+", help="Math query to process")
    parser.add_argument(
        "--log", 
        default="logs/episodes.jsonl",
        help="Path to episode log file (default: logs/episodes.jsonl)"
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Don't log episode to file"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    args = parser.parse_args()

    query = " ".join(args.query)
    
    # Import here to avoid slow startup for --help
    try:
        from quintet.math.math_mode import MathModeOrchestrator
        from quintet.core.types import (
            Episode, append_episode, compute_trust_score
        )
    except ImportError as e:
        print(f"Error importing quintet: {e}")
        print("Make sure to install with: pip install -e '.[math]'")
        return 1
    
    print(f"╔═══════════════════════════════════════════════════════════╗")
    print(f"║  Quintet Math Mode CLI                                    ║")
    print(f"╚═══════════════════════════════════════════════════════════╝")
    print(f"\n📝 Query: {query}\n")
    
    # Process query
    started_at = datetime.utcnow().isoformat()
    
    try:
        math = MathModeOrchestrator()
        result = math.process(query)
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    finished_at = datetime.utcnow().isoformat()
    
    # Build episode
    episode = Episode(
        query=query,
        mode="math",
        started_at=started_at,
        finished_at=finished_at,
        result=result,
        validation=getattr(result, "validation", None),
        world_impact=result.world_impact,
        incompleteness=result.incompleteness,
    )
    
    # Store trust score in metadata
    ts = episode.trust_score
    episode.metadata["trust_score"] = ts
    
    # Log episode
    if not args.no_log:
        try:
            append_episode(args.log, episode)
            print(f"📊 Episode logged to: {args.log}")
        except Exception as e:
            print(f"⚠️  Could not log episode: {e}")
    
    # Print results
    print(f"\n{'═' * 60}")
    print(f"RESULT")
    print(f"{'═' * 60}")
    
    if result.success:
        print(f"✅ Success")
        if hasattr(result, 'final_answer'):
            print(f"📌 Answer: {result.final_answer}")
    else:
        print(f"❌ Failed")
        for error in result.errors:
            print(f"   • {error.message}")
    
    # Print color tiles if available
    if result.color_tiles:
        print(f"\n{result.color_tiles.to_human_readable()}")
    
    # Print cognition summary if available
    if result.cognition_summary:
        cs = result.cognition_summary
        print(f"\n{'─' * 60}")
        print("COGNITION SUMMARY")
        print(f"{'─' * 60}")
        print(f"  • Observed:   {cs.observed}")
        print(f"  • Oriented:   {cs.oriented}")
        print(f"  • Acted:      {cs.acted}")
        print(f"  • Decision:   {cs.key_decision}")
        print(f"  • Rationale:  {cs.confidence_rationale}")
    
    # Print trust score
    print(f"\n{'─' * 60}")
    print(f"TRUST SCORE: {ts:.3f}")
    
    if ts >= 0.8:
        print(f"  🟢 High confidence")
    elif ts >= 0.5:
        print(f"  🟡 Moderate confidence")
    else:
        print(f"  🔴 Low confidence - review recommended")
    
    # Verbose output
    if args.verbose:
        print(f"\n{'─' * 60}")
        print("VALIDATION DETAILS")
        print(f"{'─' * 60}")
        if hasattr(result, 'validation') and result.validation:
            v = result.validation
            print(f"  Valid: {v.valid}")
            print(f"  Confidence: {v.confidence:.3f}")
            print(f"  Diversity: {v.diversity_score:.3f}")
            print(f"  Checks: {v.checks_passed}/{v.checks_passed + v.checks_failed}")
            for check in v.checks:
                status = "✓" if check.passed else "✗"
                print(f"    {status} {check.check_name}: {check.details[:50]}")
    
    print(f"\n{'═' * 60}")
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())


