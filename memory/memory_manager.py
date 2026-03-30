"""Memory Manager for coordinating STM and LTM."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import re

from .stm import ShortTermMemory, Message
from .ltm import LongTermMemory, MemoryItem


@dataclass
class MemoryContext:
    """Context retrieved from memory for LLM."""
    
    stm_messages: list[dict]  # Chat format messages from STM
    ltm_memories: list[tuple[MemoryItem, float]]  # (memory, similarity) from LTM
    
    def get_ltm_text(self) -> str:
        """Format LTM memories as text for prompt."""
        if not self.ltm_memories:
            return ""
        
        lines = ["Relevant memories:"]
        for memory, score in self.ltm_memories:
            lines.append(f"- [{memory.memory_type}] {memory.content} (relevance: {score:.2f})")
        
        return "\n".join(lines)
    
    def has_relevant_memories(self) -> bool:
        """Check if there are relevant LTM memories."""
        return len(self.ltm_memories) > 0


class MemoryManager:
    """
    Coordinates Short-Term and Long-Term Memory.
    
    Handles:
    - Memory retrieval strategy
    - Automatic consolidation from STM to LTM
    - Context building for LLM
    """
    
    def __init__(
        self,
        stm: Optional[ShortTermMemory] = None,
        ltm: Optional[LongTermMemory] = None,
        consolidate_after_turns: int = 5,
        storage_path: Optional[Path] = None,
    ):
        """
        Initialize Memory Manager.
        
        Args:
            stm: Short-Term Memory instance
            ltm: Long-Term Memory instance
            consolidate_after_turns: Consolidate STM to LTM every N turns
            storage_path: Path for memory storage
        """
        self.storage_path = Path(storage_path) if storage_path else Path("data")
        self.consolidate_after_turns = consolidate_after_turns
        
        # Initialize STM
        self.stm = stm or ShortTermMemory(
            max_turns=10,
            persist_path=self.storage_path / "stm_state.json",
        )
        
        # Initialize LTM
        self.ltm = ltm or LongTermMemory(
            storage_path=self.storage_path / "ltm",
        )
        
        self._last_consolidation_turn = 0
    
    def add_user_input(self, content: str, metadata: Optional[dict] = None) -> Message:
        """
        Process user input and add to STM.
        
        Args:
            content: User message content
            metadata: Optional metadata
            
        Returns:
            Created message
        """
        return self.stm.add_user_message(content, metadata)
    
    def add_assistant_response(self, content: str, metadata: Optional[dict] = None) -> Message:
        """
        Process assistant response and add to STM.
        
        Also triggers consolidation if needed.
        
        Args:
            content: Assistant message content
            metadata: Optional metadata
            
        Returns:
            Created message
        """
        message = self.stm.add_assistant_message(content, metadata)
        
        # Check if consolidation is needed
        turns_since_last = self.stm.turn_count - self._last_consolidation_turn
        if turns_since_last >= self.consolidate_after_turns:
            self._consolidate()
        
        return message
    
    def add_tool_result(self, content: str, tool_name: str) -> Message:
        """
        Add tool result to STM.
        
        Args:
            content: Tool result content
            tool_name: Name of the tool
            
        Returns:
            Created message
        """
        return self.stm.add_tool_message(content, tool_name)
    
    def get_context(
        self,
        include_ltm: bool = True,
        ltm_query: Optional[str] = None,
        top_k: int = 5,
    ) -> MemoryContext:
        """
        Get context from STM and LTM for LLM.
        
        Args:
            include_ltm: Whether to include LTM retrieval
            ltm_query: Custom query for LTM (uses recent context if not provided)
            top_k: Number of LTM memories to retrieve
            
        Returns:
            Memory context with STM messages and LTM memories
        """
        # Get STM messages
        stm_messages = self.stm.get_messages()
        
        # Get LTM memories
        ltm_memories = []
        if include_ltm:
            query = ltm_query or self.stm.get_recent_context(n_turns=2)
            if query:
                ltm_memories = self.ltm.search(query, top_k=top_k)
        
        return MemoryContext(
            stm_messages=stm_messages,
            ltm_memories=ltm_memories,
        )
    
    def store_memory(
        self,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        metadata: Optional[dict] = None,
    ) -> MemoryItem:
        """
        Explicitly store a memory in LTM.
        
        Args:
            content: Memory content
            memory_type: Type of memory
            importance: Importance score
            metadata: Additional metadata
            
        Returns:
            Created memory item
        """
        return self.ltm.store(
            content=content,
            memory_type=memory_type,
            importance=importance,
            metadata=metadata,
        )
    
    def search_memories(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[str] = None,
    ) -> list[tuple[MemoryItem, float]]:
        """
        Search LTM for relevant memories.
        
        Args:
            query: Search query
            top_k: Number of results
            memory_type: Optional type filter
            
        Returns:
            List of (memory, similarity) tuples
        """
        return self.ltm.search(query, top_k=top_k, memory_type=memory_type)
    
    def _consolidate(self) -> None:
        """
        Consolidate important information from STM to LTM.
        
        Extracts key facts, preferences, and tasks from conversation.
        """
        conversation_text = self.stm.get_conversation_text()
        if not conversation_text:
            return
        
        # Extract and store important information
        # This is a simple heuristic - can be enhanced with LLM-based extraction
        
        # Look for explicit "remember" instructions
        remember_patterns = [
            r"(?:remember|ingat|catat)[:\s]+(.+?)(?:\.|$)",
            r"(?:my name is|nama saya)[:\s]+(.+?)(?:\.|$)",
            r"(?:i prefer|saya suka)[:\s]+(.+?)(?:\.|$)",
        ]
        
        for pattern in remember_patterns:
            matches = re.findall(pattern, conversation_text, re.IGNORECASE)
            for match in matches:
                if match.strip():
                    self.ltm.store(
                        content=match.strip(),
                        memory_type="fact",
                        importance=0.8,
                        metadata={"source": "consolidation"},
                    )
        
        self._last_consolidation_turn = self.stm.turn_count
    
    def set_system_prompt(self, prompt: str) -> None:
        """Set system prompt in STM."""
        self.stm.set_system_message(prompt)
    
    def clear_stm(self) -> None:
        """Clear short-term memory."""
        self.stm.clear()
    
    def clear_ltm(self) -> None:
        """Clear long-term memory."""
        self.ltm.clear()
    
    def clear_all(self) -> None:
        """Clear all memory."""
        self.clear_stm()
        self.clear_ltm()
    
    def get_stats(self) -> dict:
        """Get memory statistics."""
        return {
            "stm_messages": len(self.stm),
            "stm_turns": self.stm.current_turns,
            "stm_total_turns": self.stm.turn_count,
            "ltm_memories": self.ltm.count(),
            "last_consolidation_turn": self._last_consolidation_turn,
        }
