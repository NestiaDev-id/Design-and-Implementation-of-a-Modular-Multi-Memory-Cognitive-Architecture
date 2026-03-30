"""Tool Router for executing tools based on LLM decisions."""

import json
import re
from dataclasses import dataclass, field
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from .tools.base import Tool, ToolResult, ToolResultStatus, ToolRegistry, default_registry
from .tools.calculator import CalculatorTool
from .tools.datetime_tool import DateTimeTool, MemoryTool


@dataclass
class ToolCall:
    """Represents a tool call request."""
    
    tool_name: str
    arguments: dict = field(default_factory=dict)
    
    @classmethod
    def from_text(cls, text: str) -> Optional["ToolCall"]:
        """
        Parse tool call from LLM text output.
        
        Supports formats:
        - [TOOL: name(arg1="value", arg2=123)]
        - <tool name="name" arg1="value" />
        - {"tool": "name", "arguments": {...}}
        
        Args:
            text: LLM output text
            
        Returns:
            ToolCall or None if no tool call found
        """
        # Try bracket format: [TOOL: name(args)]
        bracket_match = re.search(
            r'\[TOOL:\s*(\w+)\s*\(([^)]*)\)\s*\]',
            text,
            re.IGNORECASE,
        )
        if bracket_match:
            name = bracket_match.group(1)
            args_str = bracket_match.group(2)
            args = cls._parse_args(args_str)
            return cls(tool_name=name, arguments=args)
        
        # Try JSON format
        json_match = re.search(
            r'\{[^{}]*"tool"\s*:\s*"(\w+)"[^{}]*\}',
            text,
            re.DOTALL,
        )
        if json_match:
            try:
                # Find the full JSON object
                start = json_match.start()
                depth = 0
                end = start
                for i in range(start, len(text)):
                    if text[i] == '{':
                        depth += 1
                    elif text[i] == '}':
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                
                json_str = text[start:end]
                data = json.loads(json_str)
                
                return cls(
                    tool_name=data.get("tool", ""),
                    arguments=data.get("arguments", {}),
                )
            except json.JSONDecodeError:
                pass
        
        # Try XML-like format: <tool name="..." />
        xml_match = re.search(
            r'<tool\s+name="(\w+)"([^>]*)/?>', 
            text,
            re.IGNORECASE,
        )
        if xml_match:
            name = xml_match.group(1)
            attrs_str = xml_match.group(2)
            args = {}
            
            for attr_match in re.finditer(r'(\w+)="([^"]*)"', attrs_str):
                args[attr_match.group(1)] = attr_match.group(2)
            
            return cls(tool_name=name, arguments=args)
        
        return None
    
    @staticmethod
    def _parse_args(args_str: str) -> dict:
        """Parse argument string into dictionary."""
        args = {}
        
        # Match key=value or key="value" patterns
        for match in re.finditer(r'(\w+)\s*=\s*(?:"([^"]*)"|(\d+(?:\.\d+)?)|(\w+))', args_str):
            key = match.group(1)
            # Value is in group 2 (quoted), 3 (number), or 4 (unquoted)
            if match.group(2) is not None:
                value = match.group(2)
            elif match.group(3) is not None:
                value = float(match.group(3)) if '.' in match.group(3) else int(match.group(3))
            elif match.group(4) is not None:
                value = match.group(4)
                # Convert boolean strings
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
            else:
                value = None
            
            args[key] = value
        
        return args


class ToolRouter:
    """
    Routes and executes tool calls.
    
    Manages tool registration, execution, and result formatting.
    """
    
    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        timeout: float = 30.0,
        memory_manager = None,
    ):
        """
        Initialize Tool Router.
        
        Args:
            registry: Tool registry to use
            timeout: Execution timeout in seconds
            memory_manager: Memory manager for memory tool
        """
        self.registry = registry or ToolRegistry()
        self.timeout = timeout
        self._memory_manager = memory_manager
        
        # Register default tools
        self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register built-in tools."""
        self.registry.register(CalculatorTool())
        self.registry.register(DateTimeTool())
        
        # Memory tool with manager reference
        memory_tool = MemoryTool(self._memory_manager)
        self.registry.register(memory_tool)
    
    def set_memory_manager(self, memory_manager) -> None:
        """Set memory manager for memory tool."""
        self._memory_manager = memory_manager
        
        # Update memory tool
        memory_tool = self.registry.get("memory")
        if memory_tool and isinstance(memory_tool, MemoryTool):
            memory_tool.set_memory_manager(memory_manager)
    
    def register_tool(self, tool: Tool) -> None:
        """Register a new tool."""
        self.registry.register(tool)
    
    def parse_tool_call(self, text: str) -> Optional[ToolCall]:
        """
        Parse tool call from LLM output.
        
        Args:
            text: LLM output text
            
        Returns:
            ToolCall or None
        """
        return ToolCall.from_text(text)
    
    def has_tool_call(self, text: str) -> bool:
        """Check if text contains a tool call."""
        return self.parse_tool_call(text) is not None
    
    def execute(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a tool call.
        
        Args:
            tool_call: Tool call to execute
            
        Returns:
            Tool result
        """
        # Get tool
        tool = self.registry.get(tool_call.tool_name)
        if tool is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                output=None,
                error=f"Unknown tool: {tool_call.tool_name}",
            )
        
        # Execute with timeout
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(tool.execute, **tool_call.arguments)
                result = future.result(timeout=self.timeout)
                return result
        except FuturesTimeoutError:
            return ToolResult(
                status=ToolResultStatus.TIMEOUT,
                output=None,
                error=f"Tool execution timed out after {self.timeout}s",
            )
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                output=None,
                error=f"Tool execution error: {str(e)}",
            )
    
    def execute_from_text(self, text: str) -> Optional[ToolResult]:
        """
        Parse and execute tool call from text.
        
        Args:
            text: LLM output text
            
        Returns:
            Tool result or None if no tool call
        """
        tool_call = self.parse_tool_call(text)
        if tool_call is None:
            return None
        
        return self.execute(tool_call)
    
    def get_tools_prompt(self) -> str:
        """
        Get tool descriptions for system prompt.
        
        Returns:
            Formatted tool descriptions
        """
        if len(self.registry) == 0:
            return ""
        
        lines = [
            "You have access to the following tools:",
            "",
        ]
        
        for tool in self.registry.list_tools():
            lines.append(f"### {tool.name}")
            lines.append(f"{tool.description}")
            lines.append("")
            
            if tool.parameters:
                lines.append("Parameters:")
                for param in tool.parameters:
                    req = "(required)" if param.required else "(optional)"
                    lines.append(f"- {param.name} ({param.type}) {req}: {param.description}")
                lines.append("")
        
        lines.extend([
            "To use a tool, format your response as:",
            '[TOOL: tool_name(param1="value1", param2=value2)]',
            "",
            "Example:",
            '[TOOL: calculator(expression="2 + 2")]',
            "",
        ])
        
        return "\n".join(lines)
    
    def format_tool_result(self, tool_name: str, result: ToolResult) -> str:
        """
        Format tool result for LLM context.
        
        Args:
            tool_name: Name of the tool
            result: Tool result
            
        Returns:
            Formatted result string
        """
        if result.is_success:
            return f"[Tool Result - {tool_name}]: {result.output}"
        else:
            return f"[Tool Error - {tool_name}]: {result.error}"
