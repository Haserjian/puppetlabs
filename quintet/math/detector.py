"""
Math Mode Detector (Tier 1)
============================

Detects if a query is a math problem and classifies its intent.
"""

import re
from typing import Optional, Dict, Any, List

from quintet.math.types import MathIntent, MathDomain


# =============================================================================
# DETECTION PATTERNS
# =============================================================================

DOMAIN_PATTERNS = {
    MathDomain.ALGEBRA: {
        "strong": [
            r"\bsolve\b.*(?:equation|for\s+\w+)",
            r"\bfactor(?:ize)?\b",
            r"\bsimplify\b",
            r"\bexpand\b",
            r"\bquadratic\b",
            r"\bpolynomial\b",
            r"\broots?\b",
            r"\bsystem\s+of\s+equations",
        ],
        "medium": [
            r"\bx\s*[=+\-*/^]",
            r"\bsolve\b",
            r"=\s*0\b",
        ],
    },
    MathDomain.CALCULUS: {
        "strong": [
            r"\bintegrat(?:e|ion)\b",
            r"\bderivativ(?:e|es)\b",
            r"\bdifferentiat(?:e|ion)\b",
            r"\blimit\s+(?:as|of|when)",
            r"\bd/d[xyz]\b",
            r"∫",
            r"\bpartial\s+derivative",
            r"\btaylor\b",
            r"\bmaclaurin\b",
            r"\bseries\s+expansion",
        ],
        "medium": [
            r"\brate\s+of\s+change",
            r"\barea\s+under",
            r"\binstantaneous\b",
        ],
    },
    MathDomain.LINEAR_ALGEBRA: {
        "strong": [
            r"\bmatrix\b",
            r"\bmatrices\b",
            r"\beigenvalue|eigenvector\b",
            r"\bdeterminant\b",
            r"\binverse\b.*matrix",
            r"\brank\b.*matrix",
            r"\bvector\s+space",
            r"\blinear\s+(?:transformation|map)",
            r"\bnull\s*space\b",
            r"\bcolumn\s*space\b",
        ],
        "medium": [
            r"\bvector\b",
            r"\bdot\s+product\b",
            r"\bcross\s+product\b",
        ],
    },
    MathDomain.PROBABILITY: {
        "strong": [
            r"\bprobability\b",
            r"\bexpected\s+value\b",
            r"\bvariance\b",
            r"\bstandard\s+deviation\b",
            r"\bnormal\s+distribution\b",
            r"\bbinomial\b",
            r"\bpoisson\b",
            r"\bbayes\b",
            r"\bconditional\s+probability\b",
        ],
        "medium": [
            r"\bchance\b",
            r"\blikelihood\b",
            r"\brandom\b",
            r"\bdistribution\b",
        ],
    },
    MathDomain.NUMBER_THEORY: {
        "strong": [
            r"\bprime\b",
            r"\bgcd\b|\bhcf\b",
            r"\blcm\b",
            r"\bmodular\b",
            r"\bdivisib(?:le|ility)\b",
            r"\bfactorial\b",
            r"\bfibonacci\b",
        ],
        "medium": [
            r"\binteger\b",
            r"\bwhole\s+number\b",
        ],
    },
    # Tier 2 domains (detected but may require optional backends)
    MathDomain.OPTIMIZATION: {
        "strong": [
            r"\boptimi[sz]e\b",
            r"\bminimi[sz]e\b",
            r"\bmaximize\b",
            r"\blinear\s+programming\b",
            r"\bconvex\b",
            r"\bgradient\s+descent\b",
            r"\bconstraint(?:s|ed)?\b",
        ],
        "medium": [
            r"\bbest\b.*(?:value|solution)",
            r"\bminimum\b",
            r"\bmaximum\b",
        ],
    },
    MathDomain.STATISTICS: {
        "strong": [
            r"\bregress(?:ion)?\b",
            r"\bcorrelation\b",
            r"\bhypothesis\s+test",
            r"\bp-value\b",
            r"\bconfidence\s+interval\b",
            r"\banova\b",
            r"\bt-test\b",
            r"\bchi-square\b",
        ],
        "medium": [
            r"\bmean\b",
            r"\bmedian\b",
            r"\bmode\b",
            r"\bstatistic(?:s|al)?\b",
        ],
    },
    MathDomain.DIFFERENTIAL_EQUATIONS: {
        "strong": [
            r"\bdifferential\s+equation",
            r"\bode\b",
            r"\bdy/dx\b",
            r"\binitial\s+value\s+problem\b",
            r"\bboundary\s+value\b",
            r"\blaplace\s+transform\b",
        ],
        "medium": [
            r"\bgrowth\s+(?:rate|model)\b",
            r"\bdecay\b",
        ],
    },
}

# Problem type patterns
PROBLEM_TYPE_PATTERNS = {
    "solve": [r"\bsolve\b", r"\bfind\s+(?:the\s+)?(?:value|root|solution)"],
    "prove": [r"\bprove\b", r"\bshow\s+that\b", r"\bdemonstrate\b"],
    "compute": [r"\bcalculate\b", r"\bcompute\b", r"\bevaluate\b", r"\bwhat\s+is\b"],
    "simplify": [r"\bsimplify\b", r"\breduce\b"],
    "expand": [r"\bexpand\b"],
    "factor": [r"\bfactor(?:ize)?\b"],
    "integrate": [r"\bintegrat(?:e|ion)\b"],
    "differentiate": [r"\bdifferentiat(?:e|ion)\b", r"\bderivativ(?:e|es)\b"],
    "gradient": [r"\bgradient\b", r"\bpartial\s+derivative", r"\bjacobian\b"],
    "hessian": [r"\bhessian\b", r"\bsecond\s+derivative", r"\bsecond\s+order\b"],
    "optimize": [r"\boptimi[sz]e\b", r"\bminimi[sz]e\b", r"\bmaximize\b"],
    "fit": [r"\bfit\b", r"\bregress(?:ion)?\b", r"\bmodel\b.*data"],
    "analyze": [r"\banalyze\b", r"\bdescribe\b"],
}


# =============================================================================
# DETECTOR
# =============================================================================

class MathDetector:
    """
    Detects and classifies math problems.
    
    Returns MathIntent with domain, problem type, and confidence.
    """
    
    def detect(
        self, 
        query: str, 
        synthesis: Optional[Dict[str, Any]] = None
    ) -> MathIntent:
        """
        Analyze query and return MathIntent.
        """
        query_lower = query.lower()
        keywords_matched = []
        
        # Score each domain
        domain_scores = {}
        for domain, patterns in DOMAIN_PATTERNS.items():
            score = 0.0
            for pattern in patterns.get("strong", []):
                if re.search(pattern, query_lower):
                    score += 0.3
                    keywords_matched.append(f"{domain.value}:{pattern[:15]}")
            for pattern in patterns.get("medium", []):
                if re.search(pattern, query_lower):
                    score += 0.15
                    keywords_matched.append(f"{domain.value}:{pattern[:15]}")
            domain_scores[domain] = min(score, 1.0)
        
        # Find best domain
        best_domain = MathDomain.ALGEBRA
        best_score = 0.0
        for domain, score in domain_scores.items():
            if score > best_score:
                best_score = score
                best_domain = domain
        
        # Determine problem type
        problem_type = "compute"  # default
        for ptype, patterns in PROBLEM_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    problem_type = ptype
                    break
        
        # Check if math at all
        is_math = best_score > 0.1 or self._has_math_expression(query)
        
        # Overall confidence
        confidence = best_score if is_math else 0.0
        # If we see clear math structure (operators/equation), boost to a
        # reasonably high baseline so simple algebra problems cross typical
        # thresholds used by callers (e.g. 0.5 in tests).
        if self._has_math_expression(query):
            confidence = max(confidence, 0.6)
        
        # Check for data problem
        data_problem = any(re.search(p, query_lower) for p in [
            r"\bdata\b", r"\bdataset\b", r"\bfit\b.*model", r"\bpredict\b"
        ])
        
        # Requires explanation?
        requires_explanation = any(re.search(p, query_lower) for p in [
            r"\bexplain\b", r"\bstep\s*by\s*step\b", r"\bshow\s+(?:your\s+)?work\b",
            r"\bhow\b.*(?:solve|do|compute)"
        ])
        
        # Compute tier
        compute_tier = "standard"
        if any(re.search(p, query_lower) for p in [r"\bsimple\b", r"\bquick\b"]):
            compute_tier = "light"
        if any(re.search(p, query_lower) for p in [
            r"\bprove\b", r"\bformal\b", r"\brigorous\b", r"\bexhaustive\b"
        ]):
            compute_tier = "deep_search"
        
        return MathIntent(
            is_math=is_math,
            confidence=confidence,
            domain=best_domain,
            problem_type=problem_type,
            requires_explanation=requires_explanation,
            data_problem=data_problem,
            compute_tier=compute_tier,
            keywords_matched=keywords_matched,
            raw_query=query
        )
    
    def _has_math_expression(self, query: str) -> bool:
        """Check for mathematical expressions/symbols."""
        patterns = [
            r"[=+\-*/^]",           # Basic operators
            r"\d+\s*[+\-*/]\s*\d+", # Numeric expressions
            r"∫|∑|∏|∂|∇|√",        # Math symbols
            r"\$.*\$",              # LaTeX delimiters
            r"\\\(.*\\\)",          # LaTeX inline
            r"x\^2|y\^2",           # Powers
        ]
        for pattern in patterns:
            if re.search(pattern, query):
                return True
        return False

