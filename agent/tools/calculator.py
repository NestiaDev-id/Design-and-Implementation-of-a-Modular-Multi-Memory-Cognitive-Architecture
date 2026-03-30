"""Calculator tool for Cognitive Memory System."""

import math
import re
from typing import Union

from .base import Tool, ToolResult, ToolResultStatus, ToolParameter


class CalculatorTool(Tool):
    """Tool for mathematical calculations."""
    
    name = "calculator"
    description = "Performs mathematical calculations. Supports basic arithmetic (+, -, *, /), powers (**), and math functions (sin, cos, sqrt, log, etc.)"
    parameters = [
        ToolParameter(
            name="expression",
            description="Mathematical expression to evaluate (e.g., '2 + 3 * 4', 'sqrt(16)', 'sin(3.14)')",
            type="string",
            required=True,
        ),
    ]
    
    # Allowed functions from math module
    ALLOWED_FUNCTIONS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        # Math functions
        "sqrt": math.sqrt,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "asin": math.asin,
        "acos": math.acos,
        "atan": math.atan,
        "log": math.log,
        "log10": math.log10,
        "log2": math.log2,
        "exp": math.exp,
        "floor": math.floor,
        "ceil": math.ceil,
        "factorial": math.factorial,
        "gcd": math.gcd,
        "degrees": math.degrees,
        "radians": math.radians,
    }
    
    # Allowed constants
    ALLOWED_CONSTANTS = {
        "pi": math.pi,
        "e": math.e,
        "tau": math.tau,
        "inf": math.inf,
    }
    
    def execute(self, expression: str) -> ToolResult:
        """
        Execute mathematical calculation.
        
        Args:
            expression: Mathematical expression
            
        Returns:
            Calculation result
        """
        try:
            # Sanitize expression
            sanitized = self._sanitize_expression(expression)
            
            # Create safe evaluation context
            safe_dict = {
                "__builtins__": {},
                **self.ALLOWED_FUNCTIONS,
                **self.ALLOWED_CONSTANTS,
            }
            
            # Evaluate expression
            result = eval(sanitized, safe_dict)
            
            # Format result
            if isinstance(result, float):
                # Round to reasonable precision
                if result == int(result):
                    result = int(result)
                else:
                    result = round(result, 10)
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=result,
                metadata={"expression": expression},
            )
            
        except ZeroDivisionError:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                output=None,
                error="Division by zero",
            )
        except ValueError as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                output=None,
                error=f"Math error: {str(e)}",
            )
        except SyntaxError:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                output=None,
                error="Invalid expression syntax",
            )
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                output=None,
                error=f"Calculation error: {str(e)}",
            )
    
    def _sanitize_expression(self, expression: str) -> str:
        """
        Sanitize expression for safe evaluation.
        
        Args:
            expression: Raw expression
            
        Returns:
            Sanitized expression
        """
        # Remove whitespace
        expr = expression.strip()
        
        # Replace common alternatives
        replacements = {
            "×": "*",
            "÷": "/",
            "^": "**",
            "√": "sqrt",
        }
        
        for old, new in replacements.items():
            expr = expr.replace(old, new)
        
        # Check for disallowed patterns
        disallowed_patterns = [
            r"__",  # Dunder methods
            r"import",
            r"exec",
            r"eval",
            r"compile",
            r"open",
            r"file",
            r"input",
            r"print",
        ]
        
        for pattern in disallowed_patterns:
            if re.search(pattern, expr, re.IGNORECASE):
                raise ValueError(f"Disallowed pattern: {pattern}")
        
        return expr
