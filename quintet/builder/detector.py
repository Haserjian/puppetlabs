"""
Build Mode Detector
====================

Detects if a query is a build request and classifies its intent.
"""

import re
from typing import Optional, Dict, Any, List

from quintet.builder.types import BuildIntent, BuildCategory


# =============================================================================
# DETECTION PATTERNS
# =============================================================================

CATEGORY_PATTERNS = {
    BuildCategory.CREATE_FILE: {
        "strong": [
            r"\bcreate\b.*(?:file|script)",
            r"\bwrite\b.*(?:file|script)",
            r"\bmake\b.*(?:file|script)",
            r"\bgenerate\b.*(?:file|code)",
        ],
        "medium": [
            r"\bnew\s+file\b",
        ]
    },
    BuildCategory.CREATE_MODULE: {
        "strong": [
            r"\bcreate\b.*(?:module|package|library|class)",
            r"\bbuild\b.*(?:module|package|library)",
            r"\bimplement\b.*(?:module|class|service)",
        ],
        "medium": [
            r"\bnew\s+module\b",
            r"\bnew\s+class\b",
        ]
    },
    BuildCategory.CREATE_PROJECT: {
        "strong": [
            r"\bcreate\b.*(?:project|app|application)",
            r"\bbuild\b.*(?:project|app|application|website|api)",
            r"\bset\s*up\b.*(?:project|app)",
            r"\binitialize\b.*(?:project|repo)",
            r"\bbootstrap\b",
            r"\bscaffold\b",
        ],
        "medium": [
            r"\bnew\s+(?:project|app)\b",
        ]
    },
    BuildCategory.MODIFY_FILE: {
        "strong": [
            r"\bmodify\b",
            r"\bchange\b.*(?:file|code)",
            r"\bupdate\b.*(?:file|code|function)",
            r"\bedit\b",
        ],
        "medium": [
            r"\btweak\b",
        ]
    },
    BuildCategory.REFACTOR: {
        "strong": [
            r"\brefactor\b",
            r"\brestructure\b",
            r"\breorganize\b",
            r"\bclean\s*up\b",
            r"\bsimplify\b.*(?:code|function|module)",
        ],
        "medium": [
            r"\bimprove\b.*(?:code|structure)",
        ]
    },
    BuildCategory.ADD_FEATURE: {
        "strong": [
            r"\badd\b.*(?:feature|functionality|capability)",
            r"\bimplement\b.*(?:feature|functionality)",
            r"\bbuild\b.*(?:feature|functionality)",
            r"\badd\b.*(?:login|auth|button|form|page|endpoint|route)",
        ],
        "medium": [
            r"\bextend\b",
            r"\benhance\b",
        ]
    },
    BuildCategory.FIX_BUG: {
        "strong": [
            r"\bfix\b.*(?:bug|issue|error|problem)",
            r"\bdebug\b",
            r"\bresolve\b.*(?:issue|error)",
            r"\bpatch\b",
        ],
        "medium": [
            r"\bfix\b",
            r"\bcorrect\b",
        ]
    },
    BuildCategory.ADD_TESTS: {
        "strong": [
            r"\badd\b.*(?:test|tests|testing)",
            r"\bwrite\b.*(?:test|tests)",
            r"\bcreate\b.*(?:test|tests)",
            r"\bunit\s+test\b",
            r"\bintegration\s+test\b",
        ],
        "medium": [
            r"\btest\b",
        ]
    },
    BuildCategory.CONFIGURE: {
        "strong": [
            r"\bconfigure\b",
            r"\bset\s*up\b.*(?:config|environment|database)",
            r"\binstall\b.*(?:dependencies|packages)",
        ],
        "medium": [
            r"\bconfig\b",
            r"\bsettings\b",
        ]
    },
    BuildCategory.DEPLOY: {
        "strong": [
            r"\bdeploy\b",
            r"\bpublish\b",
            r"\brelease\b",
            r"\bship\b",
        ],
        "medium": [
            r"\blaunch\b",
        ]
    },
}

# Technology detection patterns
TECHNOLOGY_PATTERNS = {
    "python": [r"\.py\b", r"\bpython\b", r"\bpip\b", r"\bdjango\b", r"\bflask\b", r"\bfastapi\b"],
    "javascript": [r"\.js\b", r"\bjavascript\b", r"\bnode\b", r"\bnpm\b", r"\breact\b", r"\bvue\b"],
    "typescript": [r"\.ts\b", r"\btypescript\b"],
    "rust": [r"\.rs\b", r"\brust\b", r"\bcargo\b"],
    "go": [r"\.go\b", r"\bgolang\b"],
    "java": [r"\.java\b", r"\bjava\b", r"\bmaven\b", r"\bgradle\b"],
    "c++": [r"\.cpp\b", r"\.cc\b", r"\bc\+\+\b"],
    "html": [r"\.html\b", r"\bhtml\b"],
    "css": [r"\.css\b", r"\bcss\b", r"\bsass\b", r"\bscss\b"],
    "sql": [r"\.sql\b", r"\bsql\b", r"\bdatabase\b", r"\bpostgres\b", r"\bmysql\b"],
}


# =============================================================================
# DETECTOR
# =============================================================================

class BuilderDetector:
    """
    Detects and classifies build requests.
    
    Returns BuildIntent with category, confidence, and context.
    """
    
    def detect(
        self,
        query: str,
        synthesis: Optional[Dict[str, Any]] = None
    ) -> BuildIntent:
        """
        Analyze query and return BuildIntent.
        """
        query_lower = query.lower()
        keywords_matched = []
        
        # Score each category
        category_scores = {}
        for category, patterns in CATEGORY_PATTERNS.items():
            score = 0.0
            for pattern in patterns.get("strong", []):
                if re.search(pattern, query_lower):
                    score += 0.3
                    keywords_matched.append(f"{category.value}:{pattern[:15]}")
            for pattern in patterns.get("medium", []):
                if re.search(pattern, query_lower):
                    score += 0.15
                    keywords_matched.append(f"{category.value}:{pattern[:15]}")
            category_scores[category] = min(score, 1.0)
        
        # Find best category
        best_category = BuildCategory.CREATE_FILE
        best_score = 0.0
        for category, score in category_scores.items():
            if score > best_score:
                best_score = score
                best_category = category
        
        # Detect technologies
        technologies = []
        for tech, patterns in TECHNOLOGY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    technologies.append(tech)
                    break
        
        # Extract target files/modules
        target_files = self._extract_file_paths(query)
        target_modules = self._extract_module_names(query)
        
        # Check if build at all
        is_build = best_score > 0.1
        
        # Boost confidence if we have concrete targets
        confidence = best_score
        if target_files or target_modules:
            confidence = max(confidence, 0.4)
        if technologies:
            confidence = max(confidence, 0.35)
        
        return BuildIntent(
            is_build=is_build,
            confidence=confidence,
            category=best_category,
            description=self._generate_description(best_category, query),
            target_files=target_files,
            target_modules=target_modules,
            technologies=technologies,
            keywords_matched=keywords_matched,
            raw_query=query
        )
    
    def _extract_file_paths(self, query: str) -> List[str]:
        """Extract file paths from query."""
        # Match patterns like "file.py", "src/module.js", etc.
        pattern = r'\b[\w./\\-]+\.(?:py|js|ts|jsx|tsx|java|go|rs|cpp|c|h|html|css|json|yaml|yml|toml|md)\b'
        matches = re.findall(pattern, query)
        return list(set(matches))
    
    def _extract_module_names(self, query: str) -> List[str]:
        """Extract module/class names from query."""
        # Match patterns like "AuthService", "UserController", etc.
        pattern = r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b'
        matches = re.findall(pattern, query)
        return list(set(matches))
    
    def _generate_description(self, category: BuildCategory, query: str) -> str:
        """Generate a description of the build intent."""
        descriptions = {
            BuildCategory.CREATE_FILE: "Create new file(s)",
            BuildCategory.CREATE_MODULE: "Create new module/package",
            BuildCategory.CREATE_PROJECT: "Create new project",
            BuildCategory.MODIFY_FILE: "Modify existing file(s)",
            BuildCategory.REFACTOR: "Refactor code",
            BuildCategory.ADD_FEATURE: "Add new feature",
            BuildCategory.FIX_BUG: "Fix bug/issue",
            BuildCategory.ADD_TESTS: "Add tests",
            BuildCategory.CONFIGURE: "Configure project",
            BuildCategory.DEPLOY: "Deploy project",
        }
        return descriptions.get(category, "Build request")


