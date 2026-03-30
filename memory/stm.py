"""Short-Term Memory (STM) implementation for Cognitive Memory System."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from collections import deque
import json
from pathlib import Path


@dataclass
class Message:
    """Represents a single message in conversation."""
    
    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
        )
    
    def to_chat_format(self) -> dict:
        """Convert to LLM chat format."""
        return {"role": self.role, "content": self.content}


@dataclass
class ConversationTurn:
    """Represents a single turn (user input + assistant response)."""
    
    user_message: Message
    assistant_message: Optional[Message] = None
    tool_calls: list[Message] = field(default_factory=list)
    
    def is_complete(self) -> bool:
        """Check if turn has both user and assistant messages."""
        return self.assistant_message is not None
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "user_message": self.user_message.to_dict(),
            "assistant_message": self.assistant_message.to_dict() if self.assistant_message else None,
            "tool_calls": [m.to_dict() for m in self.tool_calls],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConversationTurn":
        """Create from dictionary."""
        return cls(
            user_message=Message.from_dict(data["user_message"]),
            assistant_message=Message.from_dict(data["assistant_message"]) if data.get("assistant_message") else None,
            tool_calls=[Message.from_dict(m) for m in data.get("tool_calls", [])],
        )


class ShortTermMemory:
    """
    Short-Term Memory for managing conversation history.
    
    Uses a sliding window approach to maintain recent conversation context.
    Automatically prunes old turns when max capacity is reached.
    """
    
    def __init__(
        self,
        max_turns: int = 10,
        max_tokens: int = 4096,
        persist_path: Optional[Path] = None,
    ):
        """
        Initialize STM.
        
        Args:
            max_turns: Maximum number of conversation turns to keep
            max_tokens: Maximum token count (approximate)
            persist_path: Optional path to persist STM state
        """
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.persist_path = persist_path
        
        self._turns: deque[ConversationTurn] = deque(maxlen=max_turns)
        self._current_turn: Optional[ConversationTurn] = None
        self._system_message: Optional[Message] = None
        self._turn_count: int = 0  # Total turns processed
        
        # Load persisted state if available
        if persist_path and persist_path.exists():
            self._load()
    
    @property
    def turn_count(self) -> int:
        """Total number of turns processed."""
        return self._turn_count
    
    @property
    def current_turns(self) -> int:
        """Number of turns currently in memory."""
        return len(self._turns) + (1 if self._current_turn else 0)
    
    def set_system_message(self, content: str) -> None:
        """Set the system message."""
        self._system_message = Message(role="system", content=content)
    
    def add_user_message(self, content: str, metadata: Optional[dict] = None) -> Message:
        """
        Add a user message, starting a new turn.
        
        Args:
            content: User message content
            metadata: Optional metadata
            
        Returns:
            Created message
        """
        # Complete previous turn if exists
        if self._current_turn and self._current_turn.is_complete():
            self._turns.append(self._current_turn)
        
        message = Message(
            role="user",
            content=content,
            metadata=metadata or {},
        )
        self._current_turn = ConversationTurn(user_message=message)
        
        return message
    
    def add_assistant_message(self, content: str, metadata: Optional[dict] = None) -> Message:
        """
        Add an assistant message to current turn.
        
        Args:
            content: Assistant message content
            metadata: Optional metadata
            
        Returns:
            Created message
        """
        if self._current_turn is None:
            raise ValueError("No current turn. Add user message first.")
        
        message = Message(
            role="assistant",
            content=content,
            metadata=metadata or {},
        )
        self._current_turn.assistant_message = message
        self._turn_count += 1
        
        # Save state if persistence enabled
        if self.persist_path:
            self._save()
        
        return message
    
    def add_tool_message(self, content: str, tool_name: str) -> Message:
        """
        Add a tool result message to current turn.
        
        Args:
            content: Tool result content
            tool_name: Name of the tool
            
        Returns:
            Created message
        """
        if self._current_turn is None:
            raise ValueError("No current turn. Add user message first.")
        
        message = Message(
            role="tool",
            content=content,
            metadata={"tool_name": tool_name},
        )
        self._current_turn.tool_calls.append(message)
        
        return message
    
    def get_messages(self, include_system: bool = True) -> list[dict]:
        """
        Get all messages in chat format for LLM.
        
        Args:
            include_system: Whether to include system message
            
        Returns:
            List of messages in chat format
        """
        messages = []
        
        # Add system message
        if include_system and self._system_message:
            messages.append(self._system_message.to_chat_format())
        
        # Add completed turns
        for turn in self._turns:
            messages.append(turn.user_message.to_chat_format())
            for tool_msg in turn.tool_calls:
                messages.append(tool_msg.to_chat_format())
            if turn.assistant_message:
                messages.append(turn.assistant_message.to_chat_format())
        
        # Add current turn
        if self._current_turn:
            messages.append(self._current_turn.user_message.to_chat_format())
            for tool_msg in self._current_turn.tool_calls:
                messages.append(tool_msg.to_chat_format())
            if self._current_turn.assistant_message:
                messages.append(self._current_turn.assistant_message.to_chat_format())
        
        return messages
    
    def get_conversation_text(self) -> str:
        """Get conversation as plain text for summarization."""
        lines = []
        
        for turn in self._turns:
            lines.append(f"User: {turn.user_message.content}")
            if turn.assistant_message:
                lines.append(f"Assistant: {turn.assistant_message.content}")
        
        if self._current_turn:
            lines.append(f"User: {self._current_turn.user_message.content}")
            if self._current_turn.assistant_message:
                lines.append(f"Assistant: {self._current_turn.assistant_message.content}")
        
        return "\n".join(lines)
    
    def get_recent_context(self, n_turns: int = 3) -> str:
        """
        Get recent context for memory retrieval queries.
        
        Args:
            n_turns: Number of recent turns to include
            
        Returns:
            Context string
        """
        turns = list(self._turns)[-n_turns:]
        if self._current_turn:
            turns.append(self._current_turn)
        
        parts = []
        for turn in turns:
            parts.append(turn.user_message.content)
            if turn.assistant_message:
                parts.append(turn.assistant_message.content)
        
        return " ".join(parts)
    
    def clear(self) -> None:
        """Clear all memory."""
        self._turns.clear()
        self._current_turn = None
        self._turn_count = 0
        
        if self.persist_path:
            self._save()
    
    def _save(self) -> None:
        """Save state to disk."""
        if not self.persist_path:
            return
        
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "system_message": self._system_message.to_dict() if self._system_message else None,
            "turns": [t.to_dict() for t in self._turns],
            "current_turn": self._current_turn.to_dict() if self._current_turn else None,
            "turn_count": self._turn_count,
        }
        
        with open(self.persist_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _load(self) -> None:
        """Load state from disk."""
        if not self.persist_path or not self.persist_path.exists():
            return
        
        with open(self.persist_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if data.get("system_message"):
            self._system_message = Message.from_dict(data["system_message"])
        
        self._turns = deque(
            [ConversationTurn.from_dict(t) for t in data.get("turns", [])],
            maxlen=self.max_turns,
        )
        
        if data.get("current_turn"):
            self._current_turn = ConversationTurn.from_dict(data["current_turn"])
        
        self._turn_count = data.get("turn_count", 0)
    
    def __len__(self) -> int:
        """Return number of messages in memory."""
        count = 0
        for turn in self._turns:
            count += 1  # User message
            count += len(turn.tool_calls)
            if turn.assistant_message:
                count += 1
        if self._current_turn:
            count += 1
            count += len(self._current_turn.tool_calls)
            if self._current_turn.assistant_message:
                count += 1
        return count
