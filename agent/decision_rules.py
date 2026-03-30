"""Decision Layer for Cognitive Memory System."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any
import re

from .tool_router import ToolRouter, ToolCall


class DecisionType(Enum):
    """Types of decisions the agent can make."""
    DIRECT_RESPONSE = "direct_response"  # Respond directly without tools/memory
    USE_TOOL = "use_tool"  # Use a tool
    RETRIEVE_MEMORY = "retrieve_memory"  # Retrieve from LTM
    STORE_MEMORY = "store_memory"  # Store to LTM
    CLARIFY = "clarify"  # Ask for clarification


@dataclass
class Decision:
    """Represents a decision made by the agent."""
    
    decision_type: DecisionType
    confidence: float = 1.0  # 0.0 to 1.0
    tool_call: Optional[ToolCall] = None
    memory_query: Optional[str] = None
    memory_content: Optional[str] = None
    reasoning: str = ""
    metadata: dict = field(default_factory=dict)


class DecisionLayer:
    """
    Decision layer for determining agent actions.
    
    Analyzes user input and context to decide whether to:
    - Respond directly
    - Use a tool
    - Retrieve/store memory
    - Ask for clarification
    """
    
    # Patterns indicating tool usage
    TOOL_PATTERNS = [
        # Math/calculation patterns
        (r'\b(?:calculate|compute|what is|berapa|hitung)\b.*\d+', "calculator"),
        (r'\d+\s*[\+\-\*\/\^]\s*\d+', "calculator"),
        (r'\b(?:sqrt|sin|cos|tan|log|factorial)\s*\(', "calculator"),
        
        # DateTime patterns
        (r'\b(?:what time|what date|current time|sekarang jam|tanggal)\b', "datetime"),
        (r'\b(?:hari apa|what day|tomorrow|yesterday|kemarin|besok)\b', "datetime"),
        
        # Memory patterns
        (r'\b(?:remember|ingat|catat|simpan)\b', "memory_store"),
        (r'\b(?:recall|what did i|apa yang saya|remind me)\b', "memory_retrieve"),
    ]
    
    # Patterns indicating memory retrieval need
    MEMORY_RETRIEVAL_PATTERNS = [
        r'\b(?:my name|nama saya|who am i|siapa saya)\b',
        r'\b(?:i told you|saya bilang|remember when)\b',
        r'\b(?:last time|sebelumnya|earlier)\b',
        r'\b(?:my preference|saya suka|i like|i prefer)\b',
    ]
    
    # Patterns indicating memory storage
    MEMORY_STORE_PATTERNS = [
        r'\b(?:remember that|ingat bahwa|my name is|nama saya adalah)\b',
        r'\b(?:i am|saya adalah|i prefer|saya suka)\b',
        r'\b(?:note that|catat bahwa|store this)\b',
    ]
    
    def __init__(self, tool_router: Optional[ToolRouter] = None, llm: Optional[Any] = None):
        """
        Initialize Decision Layer.
        
        Args:
            tool_router: Tool router for tool-related decisions
            llm: Reference to the loaded LLM instance (Dependency Injection)
        """
        self.tool_router = tool_router or ToolRouter()
        self.llm = llm  # Store the existing LLM instance
    
    def analyze(
        self,
        user_input: str,
        context: Optional[str] = None,
        available_tools: Optional[list[str]] = None,
    ) -> Decision:
        """
        Analyze user input and make a decision.
        
        Args:
            user_input: Current user input
            context: Optional conversation context
            available_tools: List of available tool names
            
        Returns:
            Decision about what action to take
        """
        input_lower = user_input.lower()
        
        # Check for tool usage patterns
        for pattern, tool_hint in self.TOOL_PATTERNS:
            if re.search(pattern, input_lower):
                if tool_hint == "calculator":
                    # Extract expression
                    expr = self._extract_math_expression(user_input)
                    if expr:
                        return Decision(
                            decision_type=DecisionType.USE_TOOL,
                            confidence=0.9,
                            tool_call=ToolCall(
                                tool_name="calculator",
                                arguments={"expression": expr},
                            ),
                            reasoning=f"Detected math request: {expr}",
                        )
                
                elif tool_hint == "datetime":
                    return Decision(
                        decision_type=DecisionType.USE_TOOL,
                        confidence=0.9,
                        tool_call=ToolCall(
                            tool_name="datetime",
                            arguments={"operation": "now"},
                        ),
                        reasoning="Detected date/time request",
                    )
                
                elif tool_hint == "memory_store":
                    content = self._extract_memory_content(user_input)
                    if content:
                        return Decision(
                            decision_type=DecisionType.STORE_MEMORY,
                            confidence=0.85,
                            memory_content=content,
                            reasoning=f"User wants to store: {content}",
                        )
                
                elif tool_hint == "memory_retrieve":
                    query = self._extract_memory_query(user_input)
                    return Decision(
                        decision_type=DecisionType.RETRIEVE_MEMORY,
                        confidence=0.85,
                        memory_query=query or user_input,
                        reasoning="User wants to recall information",
                    )
        
        # Check for memory retrieval patterns
        for pattern in self.MEMORY_RETRIEVAL_PATTERNS:
            if re.search(pattern, input_lower):
                return Decision(
                    decision_type=DecisionType.RETRIEVE_MEMORY,
                    confidence=0.8,
                    memory_query=user_input,
                    reasoning="Detected reference to stored information",
                )
        
        # Check for memory storage patterns
        for pattern in self.MEMORY_STORE_PATTERNS:
            if re.search(pattern, input_lower):
                content = self._extract_memory_content(user_input)
                if content:
                    return Decision(
                        decision_type=DecisionType.STORE_MEMORY,
                        confidence=0.8,
                        memory_content=content,
                        reasoning="Detected information to remember",
                    )
        
        # Check if input is too vague
        if len(user_input.split()) < 2 or user_input.endswith("?") and len(user_input) < 10:
            # Short or vague input - might need clarification
            pass
        
        # Default: direct response (let LLM handle it)
        return Decision(
            decision_type=DecisionType.DIRECT_RESPONSE,
            confidence=0.7,
            reasoning="No special action detected, proceeding with direct response",
        )
    
    def analyze_llm_output(self, llm_output: str) -> Decision:
        """
        Analyze LLM output for tool calls.
        
        Args:
            llm_output: LLM generated text
            
        Returns:
            Decision based on LLM output
        """
        # Check for tool call in output
        tool_call = self.tool_router.parse_tool_call(llm_output)
        if tool_call:
            return Decision(
                decision_type=DecisionType.USE_TOOL,
                confidence=1.0,
                tool_call=tool_call,
                reasoning="LLM requested tool use",
            )
        
        # No special action needed
        return Decision(
            decision_type=DecisionType.DIRECT_RESPONSE,
            confidence=1.0,
            reasoning="LLM provided direct response",
        )
    
    def _extract_math_expression(self, text: str) -> Optional[str]:
        """Extract mathematical expression from text."""
        # Try to find expression in quotes
        quoted = re.search(r'["\']([^"\']+)["\']', text)
        if quoted:
            expr = quoted.group(1)
            if any(c in expr for c in "+-*/^()"):
                return expr
        
        # Try to find expression patterns
        patterns = [
            r'(\d+(?:\.\d+)?\s*[\+\-\*\/\^]\s*\d+(?:\.\d+)?(?:\s*[\+\-\*\/\^]\s*\d+(?:\.\d+)?)*)',
            r'((?:sqrt|sin|cos|tan|log|factorial)\s*\([^)]+\))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_memory_content(self, text: str) -> Optional[str]:
        """Extract content to store from text."""
        patterns = [
            r'(?:remember|ingat|catat|simpan)\s+(?:that\s+)?(.+)',
            r'(?:my name is|nama saya)\s+(.+)',
            r'(?:i am|saya adalah)\s+(.+)',
            r'(?:i prefer|saya suka)\s+(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip().rstrip(".")
        
        return None
    
    def _extract_memory_query(self, text: str) -> Optional[str]:
        """Extract memory search query from text."""
        patterns = [
            r'(?:recall|what did i|apa yang saya|remind me about)\s+(.+)',
            r'(?:what is|apa)\s+(?:my\s+)?(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip().rstrip("?")
        
        return None
    
    def should_retrieve_memory(self, user_input: str) -> bool:
        """Quick check if memory retrieval might be needed."""
        input_lower = user_input.lower()
        
        for pattern in self.MEMORY_RETRIEVAL_PATTERNS:
            if re.search(pattern, input_lower):
                return True
        
        return False
    
    def should_store_memory(self, user_input: str, assistant_response: str) -> bool:
        """Check if response should be stored in memory."""
        combined = f"{user_input} {assistant_response}".lower()
        
        for pattern in self.MEMORY_STORE_PATTERNS:
            if re.search(pattern, combined):
                return True
        
        return False