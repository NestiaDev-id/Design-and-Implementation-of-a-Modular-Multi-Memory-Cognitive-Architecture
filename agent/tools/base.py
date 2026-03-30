"""Base tool interface for Cognitive Memory System."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, Callable
from enum import Enum


class ToolResultStatus(Enum):
    """Status of tool execution."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class ToolResult:
    """Result from tool execution."""
    
    status: ToolResultStatus
    output: Any
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    
    @property
    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ToolResultStatus.SUCCESS
    
    def to_string(self) -> str:
        """Convert result to string for LLM."""
        if self.is_success:
            return str(self.output)
        else:
            return f"Error: {self.error}"


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    
    name: str
    description: str
    type: str  # "string", "number", "boolean", "array", "object"
    required: bool = True
    default: Any = None
    enum: Optional[list] = None


class Tool(ABC):
    """Base class for all tools."""
    
    name: str = "base_tool"
    description: str = "Base tool"
    parameters: list[ToolParameter] = []
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Tool result
        """
        pass
    
    def get_schema(self) -> dict:
        """
        Get JSON schema for tool parameters.
        
        Returns:
            JSON schema dict for LLM function calling
        """
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default
            
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }
    
    def __repr__(self) -> str:
        return f"Tool({self.name})"


class FunctionTool(Tool):
    """Tool wrapper for simple functions."""
    
    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
        parameters: Optional[list[ToolParameter]] = None,
    ):
        """
        Create a tool from a function.
        
        Args:
            name: Tool name
            description: Tool description
            func: Function to wrap
            parameters: Parameter definitions
        """
        self.name = name
        self.description = description
        self._func = func
        self.parameters = parameters or []
    
    def execute(self, **kwargs) -> ToolResult:
        """Execute the wrapped function."""
        try:
            result = self._func(**kwargs)
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=result,
            )
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                output=None,
                error=str(e),
            )


class ToolRegistry:
    """Registry for managing tools."""
    
    def __init__(self):
        """Initialize registry."""
        self._tools: dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool
    
    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.
        
        Args:
            name: Tool name
            
        Returns:
            True if removed, False if not found
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[Tool]:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool or None if not found
        """
        return self._tools.get(name)
    
    def list_tools(self) -> list[Tool]:
        """Get list of all registered tools."""
        return list(self._tools.values())
    
    def get_schemas(self) -> list[dict]:
        """Get JSON schemas for all tools."""
        return [tool.get_schema() for tool in self._tools.values()]
    
    def get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions for prompt."""
        lines = ["Available tools:"]
        for tool in self._tools.values():
            params_str = ", ".join(
                f"{p.name}: {p.type}" for p in tool.parameters
            )
            lines.append(f"- {tool.name}({params_str}): {tool.description}")
        return "\n".join(lines)
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __contains__(self, name: str) -> bool:
        return name in self._tools


# Global tool registry
default_registry = ToolRegistry()


def register_tool(tool: Tool) -> None:
    """Register a tool to the default registry."""
    default_registry.register(tool)


def get_tool(name: str) -> Optional[Tool]:
    """Get a tool from the default registry."""
    return default_registry.get(name)
