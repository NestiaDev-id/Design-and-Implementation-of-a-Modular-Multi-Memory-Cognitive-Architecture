"""DateTime tool for Cognitive Memory System."""

from datetime import datetime, timedelta
from typing import Optional
import calendar

from .base import Tool, ToolResult, ToolResultStatus, ToolParameter


class DateTimeTool(Tool):
    """Tool for date and time operations."""
    
    name = "datetime"
    description = "Gets current date/time or performs date calculations. Can get current time, add/subtract days, or get day of week."
    parameters = [
        ToolParameter(
            name="operation",
            description="Operation to perform",
            type="string",
            required=True,
            enum=["now", "add_days", "weekday", "format"],
        ),
        ToolParameter(
            name="days",
            description="Number of days to add (for add_days operation)",
            type="number",
            required=False,
            default=0,
        ),
        ToolParameter(
            name="date_string",
            description="Date string in YYYY-MM-DD format (for weekday/format operations)",
            type="string",
            required=False,
        ),
        ToolParameter(
            name="format",
            description="Output format (for format operation). Use strftime format codes.",
            type="string",
            required=False,
            default="%Y-%m-%d %H:%M:%S",
        ),
    ]
    
    def execute(
        self,
        operation: str,
        days: Optional[int] = None,
        date_string: Optional[str] = None,
        format: str = "%Y-%m-%d %H:%M:%S",
    ) -> ToolResult:
        """
        Execute date/time operation.
        
        Args:
            operation: Operation to perform
            days: Days to add (for add_days)
            date_string: Date string (for weekday/format)
            format: Output format
            
        Returns:
            Operation result
        """
        try:
            if operation == "now":
                now = datetime.now()
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output={
                        "datetime": now.strftime(format),
                        "date": now.strftime("%Y-%m-%d"),
                        "time": now.strftime("%H:%M:%S"),
                        "weekday": calendar.day_name[now.weekday()],
                        "timestamp": now.timestamp(),
                    },
                )
            
            elif operation == "add_days":
                base_date = datetime.now()
                if date_string:
                    base_date = datetime.strptime(date_string, "%Y-%m-%d")
                
                days_to_add = days or 0
                result_date = base_date + timedelta(days=days_to_add)
                
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output={
                        "result_date": result_date.strftime("%Y-%m-%d"),
                        "weekday": calendar.day_name[result_date.weekday()],
                        "days_added": days_to_add,
                    },
                )
            
            elif operation == "weekday":
                if not date_string:
                    date_obj = datetime.now()
                else:
                    date_obj = datetime.strptime(date_string, "%Y-%m-%d")
                
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output={
                        "date": date_obj.strftime("%Y-%m-%d"),
                        "weekday": calendar.day_name[date_obj.weekday()],
                        "weekday_number": date_obj.weekday(),
                    },
                )
            
            elif operation == "format":
                if not date_string:
                    date_obj = datetime.now()
                else:
                    # Try multiple formats
                    for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"]:
                        try:
                            date_obj = datetime.strptime(date_string, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError(f"Could not parse date: {date_string}")
                
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output=date_obj.strftime(format),
                )
            
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    output=None,
                    error=f"Unknown operation: {operation}",
                )
                
        except ValueError as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                output=None,
                error=f"Date error: {str(e)}",
            )
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                output=None,
                error=f"DateTime error: {str(e)}",
            )


class MemoryTool(Tool):
    """Tool for explicit memory operations."""
    
    name = "memory"
    description = "Store or retrieve information from long-term memory."
    parameters = [
        ToolParameter(
            name="operation",
            description="Operation to perform",
            type="string",
            required=True,
            enum=["store", "search", "list"],
        ),
        ToolParameter(
            name="content",
            description="Content to store (for store operation)",
            type="string",
            required=False,
        ),
        ToolParameter(
            name="query",
            description="Search query (for search operation)",
            type="string",
            required=False,
        ),
        ToolParameter(
            name="memory_type",
            description="Type of memory (fact, preference, task)",
            type="string",
            required=False,
            default="fact",
            enum=["fact", "preference", "task", "conversation"],
        ),
        ToolParameter(
            name="importance",
            description="Importance score (0.0 to 1.0)",
            type="number",
            required=False,
            default=0.5,
        ),
    ]
    
    def __init__(self, memory_manager=None):
        """
        Initialize memory tool.
        
        Args:
            memory_manager: MemoryManager instance
        """
        self._memory_manager = memory_manager
    
    def set_memory_manager(self, memory_manager) -> None:
        """Set memory manager reference."""
        self._memory_manager = memory_manager
    
    def execute(
        self,
        operation: str,
        content: Optional[str] = None,
        query: Optional[str] = None,
        memory_type: str = "fact",
        importance: float = 0.5,
    ) -> ToolResult:
        """
        Execute memory operation.
        
        Args:
            operation: Operation to perform
            content: Content to store
            query: Search query
            memory_type: Memory type
            importance: Importance score
            
        Returns:
            Operation result
        """
        if self._memory_manager is None:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                output=None,
                error="Memory manager not initialized",
            )
        
        try:
            if operation == "store":
                if not content:
                    return ToolResult(
                        status=ToolResultStatus.ERROR,
                        output=None,
                        error="Content is required for store operation",
                    )
                
                memory = self._memory_manager.store_memory(
                    content=content,
                    memory_type=memory_type,
                    importance=importance,
                )
                
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output=f"Stored memory: {memory.id}",
                    metadata={"memory_id": memory.id},
                )
            
            elif operation == "search":
                if not query:
                    return ToolResult(
                        status=ToolResultStatus.ERROR,
                        output=None,
                        error="Query is required for search operation",
                    )
                
                results = self._memory_manager.search_memories(
                    query=query,
                    memory_type=memory_type if memory_type != "fact" else None,
                )
                
                if not results:
                    return ToolResult(
                        status=ToolResultStatus.SUCCESS,
                        output="No relevant memories found.",
                    )
                
                output_lines = ["Found memories:"]
                for memory, score in results:
                    output_lines.append(f"- [{memory.memory_type}] {memory.content} (relevance: {score:.2f})")
                
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output="\n".join(output_lines),
                )
            
            elif operation == "list":
                memories = self._memory_manager.ltm.get_all(
                    memory_type=memory_type if memory_type != "fact" else None
                )
                
                if not memories:
                    return ToolResult(
                        status=ToolResultStatus.SUCCESS,
                        output="No memories stored.",
                    )
                
                output_lines = [f"Stored memories ({len(memories)}):"]
                for memory in memories[:10]:  # Limit to 10
                    output_lines.append(f"- [{memory.memory_type}] {memory.content}")
                
                if len(memories) > 10:
                    output_lines.append(f"... and {len(memories) - 10} more")
                
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output="\n".join(output_lines),
                )
            
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    output=None,
                    error=f"Unknown operation: {operation}",
                )
                
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                output=None,
                error=f"Memory error: {str(e)}",
            )
