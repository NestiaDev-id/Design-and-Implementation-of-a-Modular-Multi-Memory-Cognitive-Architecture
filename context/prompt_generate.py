"""Context Builder and Prompt Generation for Cognitive Memory System."""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime

# Model path configuration
MODEL_PATH = r"E:\models\qwen\qwen2.5-1.5b-instruct"


class PromptTemplates:
    """Collection of prompt templates."""
    
    # Base system prompt
    SYSTEM_BASE = """You are a helpful AI assistant with cognitive memory capabilities.

Current date/time: {datetime}

{tools_section}

{memory_section}

Guidelines:
- Be helpful, accurate, and concise
- If you're unsure, say so
- Use tools when appropriate for calculations, dates, or memory operations
- Remember important information shared by the user
"""
    
    # Tool usage instructions
    TOOLS_SECTION = """You have access to tools for specific tasks:
{tools_description}

To use a tool, include in your response:
[TOOL: tool_name(param1="value1", param2=value2)]
"""
    
    # Memory context section
    MEMORY_SECTION = """Relevant information from memory:
{memories}
"""
    
    # Conversation summarization prompt
    SUMMARIZE_PROMPT = """Summarize the key points from this conversation that should be remembered:

{conversation}

Provide a brief summary of important facts, preferences, or tasks mentioned:"""
    
    # Memory extraction prompt
    EXTRACT_MEMORY_PROMPT = """From this conversation, extract any important information that should be stored:

User: {user_message}
Assistant: {assistant_message}

If there is something worth remembering (facts, preferences, names, tasks), output it in format:
MEMORY: [type] content

Types can be: fact, preference, task
If nothing important, output: MEMORY: none
"""


@dataclass
class BuiltContext:
    """Represents built context for LLM."""
    
    system_prompt: str
    messages: list[dict]
    has_tools: bool
    has_memories: bool
    token_estimate: int
    
    def get_full_prompt(self) -> str:
        """Get full prompt as single string (for non-chat models)."""
        parts = [f"System: {self.system_prompt}\n"]
        
        for msg in self.messages:
            role = msg["role"].capitalize()
            content = msg["content"]
            parts.append(f"{role}: {content}")
        
        parts.append("Assistant:")
        return "\n".join(parts)


class ContextBuilder:
    """
    Builds context for LLM from various sources.
    
    Combines:
    - System prompt with tools and memory
    - STM conversation history
    - Relevant LTM memories
    """
    
    def __init__(
        self,
        max_context_tokens: int = 4096,
        include_tools: bool = True,
        include_memories: bool = True,
    ):
        """
        Initialize Context Builder.
        
        Args:
            max_context_tokens: Maximum tokens for context
            include_tools: Whether to include tool descriptions
            include_memories: Whether to include LTM memories
        """
        self.max_context_tokens = max_context_tokens
        self.include_tools = include_tools
        self.include_memories = include_memories
    
    def build(
        self,
        stm_messages: list[dict],
        ltm_memories: Optional[list[tuple]] = None,
        tools_description: Optional[str] = None,
        custom_system_prompt: Optional[str] = None,
    ) -> BuiltContext:
        """
        Build context for LLM.
        
        Args:
            stm_messages: Messages from STM in chat format
            ltm_memories: List of (MemoryItem, similarity) from LTM
            tools_description: Formatted tool descriptions
            custom_system_prompt: Override default system prompt
            
        Returns:
            Built context ready for LLM
        """
        # Build tools section
        tools_section = ""
        has_tools = False
        if self.include_tools and tools_description:
            tools_section = PromptTemplates.TOOLS_SECTION.format(
                tools_description=tools_description
            )
            has_tools = True
        
        # Build memory section
        memory_section = ""
        has_memories = False
        if self.include_memories and ltm_memories:
            memory_lines = []
            for memory, score in ltm_memories:
                memory_lines.append(f"- [{memory.memory_type}] {memory.content}")
            
            if memory_lines:
                memory_section = PromptTemplates.MEMORY_SECTION.format(
                    memories="\n".join(memory_lines)
                )
                has_memories = True
        
        # Build system prompt
        if custom_system_prompt:
            system_prompt = custom_system_prompt
        else:
            system_prompt = PromptTemplates.SYSTEM_BASE.format(
                datetime=datetime.now().strftime("%Y-%m-%d %H:%M"),
                tools_section=tools_section,
                memory_section=memory_section,
            )
        
        # Clean up empty lines
        system_prompt = "\n".join(
            line for line in system_prompt.split("\n") 
            if line.strip() or line == ""
        )
        
        # Process messages - ensure system message is first
        messages = []
        
        # Check if STM already has system message
        has_system = any(m.get("role") == "system" for m in stm_messages)
        
        if not has_system:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add STM messages, updating system if present
        for msg in stm_messages:
            if msg.get("role") == "system":
                # Update with built system prompt
                messages.append({"role": "system", "content": system_prompt})
            else:
                messages.append(msg)
        
        # Estimate tokens (rough: ~4 chars per token)
        total_chars = sum(len(m.get("content", "")) for m in messages)
        token_estimate = total_chars // 4
        
        return BuiltContext(
            system_prompt=system_prompt,
            messages=messages,
            has_tools=has_tools,
            has_memories=has_memories,
            token_estimate=token_estimate,
        )
    
    def build_summarization_prompt(self, conversation_text: str) -> str:
        """Build prompt for conversation summarization."""
        return PromptTemplates.SUMMARIZE_PROMPT.format(
            conversation=conversation_text
        )
    
    def build_memory_extraction_prompt(
        self,
        user_message: str,
        assistant_message: str,
    ) -> str:
        """Build prompt for extracting memories from exchange."""
        return PromptTemplates.EXTRACT_MEMORY_PROMPT.format(
            user_message=user_message,
            assistant_message=assistant_message,
        )
    
    def add_tool_result_to_messages(
        self,
        messages: list[dict],
        tool_name: str,
        result: str,
    ) -> list[dict]:
        """
        Add tool result to message list.
        
        Args:
            messages: Current messages
            tool_name: Name of the tool
            result: Tool result string
            
        Returns:
            Updated messages
        """
        # Add as assistant message with tool result
        tool_msg = {
            "role": "assistant",
            "content": f"[Tool: {tool_name}]\nResult: {result}",
        }
        
        return messages + [tool_msg]
    
    def truncate_messages(
        self,
        messages: list[dict],
        max_tokens: Optional[int] = None,
    ) -> list[dict]:
        """
        Truncate messages to fit within token limit.
        
        Keeps system message and most recent messages.
        
        Args:
            messages: Messages to truncate
            max_tokens: Token limit (uses default if not specified)
            
        Returns:
            Truncated messages
        """
        limit = max_tokens or self.max_context_tokens
        
        # Calculate current tokens
        total_chars = sum(len(m.get("content", "")) for m in messages)
        current_tokens = total_chars // 4
        
        if current_tokens <= limit:
            return messages
        
        # Keep system message and truncate from beginning
        truncated = []
        system_msg = None
        other_msgs = []
        
        for msg in messages:
            if msg.get("role") == "system":
                system_msg = msg
            else:
                other_msgs.append(msg)
        
        if system_msg:
            truncated.append(system_msg)
            limit -= len(system_msg.get("content", "")) // 4
        
        # Add messages from end until limit reached
        for msg in reversed(other_msgs):
            msg_tokens = len(msg.get("content", "")) // 4
            if msg_tokens <= limit:
                truncated.insert(1 if system_msg else 0, msg)
                limit -= msg_tokens
            else:
                break
        
        return truncated


# Default context builder instance
default_builder = ContextBuilder()
