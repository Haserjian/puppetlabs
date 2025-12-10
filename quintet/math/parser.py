"""
Math Mode Parser (Tier 1)
==========================

Parses natural language math queries into structured MathProblem objects.
"""

import re
from typing import Optional, Dict, Any, List, Union
import uuid

from quintet.math.types import (
    MathIntent, MathExpression, MathProblem, DataProblem, MathDomain
)


class ProblemParser:
    """
    Parses math queries into structured problem representations.
    
    Tier 1: Basic parsing with SymPy integration for expressions.
    """
    
    def __init__(self):
        # Try to import sympy for expression parsing
        try:
            import sympy
            self.sympy = sympy
            self.sympy_available = True
        except ImportError:
            self.sympy = None
            self.sympy_available = False
    
    def parse(
        self,
        query: str,
        intent: MathIntent,
        synthesis: Optional[Dict[str, Any]] = None
    ) -> Union[MathProblem, DataProblem]:
        """
        Parse query into structured problem representation.
        """
        if intent.data_problem:
            return self._parse_data_problem(query, intent)
        else:
            return self._parse_math_problem(query, intent)
    
    def _parse_math_problem(self, query: str, intent: MathIntent) -> MathProblem:
        """Parse into MathProblem."""
        # Extract mathematical expressions
        expressions = self._extract_expressions(query, intent)
        
        # Extract variables
        variables = self._extract_variables(query, expressions)
        
        # Extract constraints
        constraints = self._extract_constraints(query)
        
        # Extract what we're solving for
        goal = self._extract_goal(query, intent.problem_type)
        
        return MathProblem(
            problem_id=str(uuid.uuid4()),
            domain=intent.domain,
            problem_type=intent.problem_type,
            description=query,
            expressions=expressions,
            variables=variables,
            constraints=constraints,
            goal=goal,
            raw_input=query,
            parsed_successfully=len(expressions) > 0 or len(variables) > 0
        )
    
    def _parse_data_problem(self, query: str, intent: MathIntent) -> DataProblem:
        """Parse into DataProblem."""
        # Extract data mentions
        data_source = None
        data_inline = None
        
        # Check for inline data
        data_match = re.search(
            r"data(?:\s*[:=])?\s*\{([^}]+)\}",
            query, re.IGNORECASE
        )
        if data_match:
            # Try to parse as simple dict
            data_inline = self._parse_inline_data(data_match.group(1))
        
        # Check for file reference
        file_match = re.search(r"from\s+([^\s]+\.(?:csv|json|txt))", query)
        if file_match:
            data_source = file_match.group(1)
        
        # Extract target and features
        target = self._extract_target_variable(query)
        features = self._extract_feature_variables(query)
        
        # Model hint
        model_hint = None
        if re.search(r"\blinear\b", query.lower()):
            model_hint = "linear"
        elif re.search(r"\blogistic\b", query.lower()):
            model_hint = "logistic"
        
        return DataProblem(
            problem_id=str(uuid.uuid4()),
            domain=intent.domain,
            problem_type=intent.problem_type,
            description=query,
            data_source=data_source,
            data_inline=data_inline,
            target_variable=target,
            feature_variables=features,
            model_hint=model_hint,
            raw_input=query,
            parsed_successfully=True
        )
    
    def _extract_expressions(self, query: str, intent: MathIntent) -> List[MathExpression]:
        """
        Extract mathematical expressions from query.
        
        Notes:
        - For equation-style queries like "Solve 2x + 4 = 10" we strip leading
          verbs ("solve", "find") so SymPy sees a clean equation.
        - For calculus-style queries like "Integrate 2*x with respect to x"
          we fall back to capturing the expression between "integrate" and
          "with respect to".
        """
        expressions = []
        eq_count = query.count("=")
        
        # Pattern for equations: something = something
        eq_pattern = r"([^=,;.]+=[^=,;.]+)"
        if eq_count > 1:
            # Split on common conjunctions to isolate equations in systems
            candidates = re.split(r"\band\b|;|\n|,", query, flags=re.IGNORECASE)
            for cand in candidates:
                cand = cand.strip()
                if "=" not in cand:
                    continue
                for match in re.finditer(eq_pattern, cand):
                    expr_str = match.group(1).strip()
                    expr_str = re.sub(
                        r"^(solve|find|compute|determine)\s+",
                        "",
                        expr_str,
                        flags=re.IGNORECASE,
                    )
                    expressions.append(self._parse_expression(expr_str))
        else:
            for match in re.finditer(eq_pattern, query):
                expr_str = match.group(1).strip()
                # Drop leading verbs like "solve", "find", etc.
                expr_str = re.sub(
                    r"^(solve|find|compute|determine)\s+",
                    "",
                    expr_str,
                    flags=re.IGNORECASE,
                )
                expressions.append(self._parse_expression(expr_str))

        # Pattern for standalone expressions with variables
        # e.g., "x^2 + 2x + 1", "3x - 7"
        #
        # IMPORTANT: only run this when there are no explicit equations.
        # For systems like "Solve x + y = 5 and 2x - y = 1" it would
        # otherwise add a stray "x + y" expression, which confuses the
        # solver and can lead to empty solution sets.
        expr_pattern = r"\b([a-z]\^?\d*\s*[+\-*/]\s*[\da-z^+\-*/\s]+)"
        if eq_count == 0:
            for match in re.finditer(expr_pattern, query.lower()):
                expr_str = match.group(1).strip()
                if expr_str not in [e.raw for e in expressions]:
                    expressions.append(self._parse_expression(expr_str))

        # Calculus-specific fallback: "Integrate 2*x with respect to x"
        if not expressions and intent.problem_type == "integrate":
            calc_expr = self._extract_calculus_expression(query)
            if calc_expr:
                expressions.append(self._parse_expression(calc_expr))
        
        return expressions

    def _extract_calculus_expression(self, query: str) -> Optional[str]:
        """Best-effort extraction for calculus-style queries."""
        # "Integrate 2*x with respect to x"
        m = re.search(
            r"integrate\s+(.+?)\s+with\s+respect\s+to\s+[a-z]",
            query,
            re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()
        # "Integrate 2*x dx"
        m = re.search(
            r"integrate\s+(.+?)\s*d[xyzt]\b",
            query,
            re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()
        return None
    
    def _parse_expression(self, expr_str: str) -> MathExpression:
        """Parse a single expression string."""
        # Basic normalization
        normalized = expr_str.replace("^", "**").replace(" ", "")
        # Insert explicit multiplication between numbers and variables, e.g. 2x -> 2*x
        normalized = re.sub(r"(?<=\d)([a-zA-Z])", r"*\1", normalized)
        
        sympy_expr = None
        latex = None
        
        if self.sympy_available:
            try:
                sympy_expr = self.sympy.sympify(normalized)
                latex = self.sympy.latex(sympy_expr)
            except:
                pass  # Parsing failed, continue without sympy
        
        # Extract variables
        variables = list(set(re.findall(r"\b([a-z])\b", expr_str.lower())))
        
        # Extract operations
        operations = []
        if "+" in expr_str: operations.append("add")
        if "-" in expr_str: operations.append("subtract")
        if "*" in expr_str or re.search(r"\d[a-z]", expr_str): operations.append("multiply")
        if "/" in expr_str: operations.append("divide")
        if "^" in expr_str or "**" in expr_str: operations.append("power")
        if "sqrt" in expr_str.lower() or "√" in expr_str: operations.append("sqrt")
        
        return MathExpression(
            raw=expr_str,
            normalized=normalized,
            sympy_expr=sympy_expr,
            latex=latex,
            variables=variables,
            operations=operations
        )
    
    def _extract_variables(
        self, 
        query: str, 
        expressions: List[MathExpression]
    ) -> List[str]:
        """Extract all variables from query and expressions."""
        variables = set()
        
        # From expressions
        for expr in expressions:
            variables.update(expr.variables)
        
        # Pattern: "solve for x", "find y"
        for_match = re.search(r"(?:solve|find)\s+(?:for\s+)?([a-z])\b", query.lower())
        if for_match:
            variables.add(for_match.group(1))

        # Calculus pattern: "with respect to x"
        wrt_match = re.search(r"with\s+respect\s+to\s+([a-z])\b", query.lower())
        if wrt_match:
            variables.add(wrt_match.group(1))
        
        # General single-letter variables
        for letter in re.findall(r"\b([a-z])\b", query.lower()):
            if letter not in ['a', 'i', 'e']:  # Exclude articles and common words
                variables.add(letter)
        
        return sorted(list(variables))
    
    def _extract_constraints(self, query: str) -> List[str]:
        """Extract constraints from query."""
        constraints = []
        
        # Pattern: "where x > 0", "such that y >= 1"
        constraint_patterns = [
            r"where\s+([^,;.]+)",
            r"such\s+that\s+([^,;.]+)",
            r"subject\s+to\s+([^,;.]+)",
            r"given\s+(?:that\s+)?([^,;.]+)",
        ]
        
        for pattern in constraint_patterns:
            matches = re.findall(pattern, query.lower())
            constraints.extend(matches)
        
        return constraints
    
    def _extract_goal(self, query: str, problem_type: str) -> Optional[str]:
        """Extract what we're trying to find/solve."""
        # "solve for x" -> "x"
        match = re.search(r"solve\s+(?:for\s+)?([a-z])\b", query.lower())
        if match:
            return match.group(1)
        
        # "find the value of x" -> "x"
        match = re.search(r"find\s+(?:the\s+)?(?:value\s+of\s+)?([a-z])\b", query.lower())
        if match:
            return match.group(1)
        
        # "integrate x^2" -> integral
        if problem_type == "integrate":
            return "integral"
        
        # "differentiate x^2" -> derivative  
        if problem_type == "differentiate":
            return "derivative"
        
        return None
    
    def _extract_target_variable(self, query: str) -> Optional[str]:
        """Extract target variable for data problems."""
        patterns = [
            r"predict\s+(\w+)",
            r"(\w+)\s+(?:is|as)\s+(?:the\s+)?(?:target|dependent)",
            r"dependent\s+variable\s+(?:is\s+)?(\w+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                return match.group(1)
        return None
    
    def _extract_feature_variables(self, query: str) -> List[str]:
        """Extract feature variables for data problems."""
        features = []
        patterns = [
            r"using\s+(\w+(?:\s*,\s*\w+)*)\s+(?:to|as)\s+(?:features?|predictors?)",
            r"independent\s+variables?\s+(?:are\s+)?(\w+(?:\s*,\s*\w+)*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, query.lower())
            if match:
                features.extend(re.split(r"\s*,\s*", match.group(1)))
        return features
    
    def _parse_inline_data(self, data_str: str) -> Optional[Dict[str, List[Any]]]:
        """Parse inline data string into dict."""
        try:
            # Simple format: "x: 1,2,3; y: 4,5,6"
            result = {}
            for pair in data_str.split(";"):
                if ":" in pair:
                    key, values = pair.split(":", 1)
                    key = key.strip()
                    values = [float(v.strip()) for v in values.split(",")]
                    result[key] = values
            return result if result else None
        except:
            return None

