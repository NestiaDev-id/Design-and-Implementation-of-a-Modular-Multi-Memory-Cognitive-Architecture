"""Agent Manager - Manages CognitiveAgent instances and sessions."""

import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from dataclasses import dataclass, field
import json
import uuid

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.config import Config
from core.llm import QwenLLM
from memory.memory_manager import MemoryManager
from agent.decision_rules import DecisionLayer, DecisionType
from agent.tool_router import ToolRouter
from context.prompt_generate import ContextBuilder


@dataclass
class Session:
    """Represents a chat session."""
    id: str
    title: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    messages: list[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": self.messages,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        return cls(
            id=data["id"],
            title=data["title"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            messages=data.get("messages", []),
        )


class AgentManager:
    """
    Manages CognitiveAgent and sessions.
    
    Provides a unified interface for the API to interact with the agent.
    """
    
    _instance: Optional["AgentManager"] = None
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the agent manager."""
        self.config = config or Config()
        self.sessions: dict[str, Session] = {}
        self._sessions_path = self.config.data_path / "sessions.json"
        
        # Initialize components
        self._llm: Optional[QwenLLM] = None
        self._memory_manager: Optional[MemoryManager] = None
        self._tool_router: Optional[ToolRouter] = None
        self._decision_layer: Optional[DecisionLayer] = None
        self._context_builder: Optional[ContextBuilder] = None
        
        self._initialized = False
        
        # Load existing sessions
        self._load_sessions()
    
    @classmethod
    def get_instance(cls, config: Optional[Config] = None) -> "AgentManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance
    
    def initialize(self) -> None:
        """Initialize all components (lazy loading)."""
        if self._initialized:
            return
        
        print("Initializing AgentManager components...")
        
        # Initialize LLM
        self._llm = QwenLLM(self.config.llm)
        
        # Initialize Memory Manager
        self._memory_manager = MemoryManager(
            storage_path=self.config.data_path,
            consolidate_after_turns=self.config.memory.consolidate_after_turns,
        )
        
        # Initialize Tool Router
        self._tool_router = ToolRouter(
            timeout=self.config.agent.tool_timeout,
            memory_manager=self._memory_manager,
        )
        
        # Initialize Decision Layer
        self._decision_layer = DecisionLayer(tool_router=self._tool_router)
        
        # Initialize Context Builder
        self._context_builder = ContextBuilder(
            max_context_tokens=self.config.memory.stm_max_tokens,
            include_tools=self.config.agent.enable_tools,
        )
        
        # Set system prompt
        self._memory_manager.set_system_prompt(self._build_system_prompt())
        
        self._initialized = True
        print("AgentManager initialized!")
    
    def _build_system_prompt(self) -> str:
        """Build system prompt."""
        tools_desc = ""
        if self.config.agent.enable_tools and self._tool_router:
            tools_desc = self._tool_router.get_tools_prompt()
        
        return f"""You are a helpful AI assistant with cognitive memory capabilities.

{tools_desc}

Guidelines:
- Be helpful, accurate, and concise
- If you need to calculate something, use the calculator tool
- If you need current time/date, use the datetime tool
- Remember important information shared by the user
- You can use Bahasa Indonesia or English based on user's language
"""
    
    @property
    def llm(self) -> QwenLLM:
        if self._llm is None:
            self.initialize()
        return self._llm
    
    @property
    def memory_manager(self) -> MemoryManager:
        if self._memory_manager is None:
            self.initialize()
        return self._memory_manager
    
    @property
    def tool_router(self) -> ToolRouter:
        if self._tool_router is None:
            self.initialize()
        return self._tool_router
    
    @property
    def decision_layer(self) -> DecisionLayer:
        if self._decision_layer is None:
            self.initialize()
        return self._decision_layer
    
    @property
    def context_builder(self) -> ContextBuilder:
        if self._context_builder is None:
            self.initialize()
        return self._context_builder
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    @property
    def is_llm_loaded(self) -> bool:
        return self._llm is not None and self._llm.is_loaded
    
    # ──────────────────────────────────────────────────────────
    # Session Management
    # ──────────────────────────────────────────────────────────
    
    def create_session(self, title: str = "New Chat") -> Session:
        """Create a new session."""
        session = Session(
            id=str(uuid.uuid4()),
            title=title,
        )
        self.sessions[session.id] = session
        self._save_sessions()
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> list[Session]:
        """List all sessions, sorted by updated_at."""
        return sorted(
            self.sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True,
        )
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions()
            return True
        return False
    
    def update_session_title(self, session_id: str, title: str) -> Optional[Session]:
        """Update session title."""
        session = self.sessions.get(session_id)
        if session:
            session.title = title
            session.updated_at = datetime.now()
            self._save_sessions()
        return session
    
    def add_message_to_session(
        self,
        session_id: str,
        role: str,
        content: str,
        message_id: Optional[str] = None,
    ) -> dict:
        """Add a message to a session."""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        message = {
            "id": message_id or str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        
        session.messages.append(message)
        session.updated_at = datetime.now()
        
        # Update title from first message
        if len(session.messages) == 1 and role == "user":
            session.title = content[:30] + ("..." if len(content) > 30 else "")
        
        self._save_sessions()
        return message
    
    def _load_sessions(self) -> None:
        """Load sessions from disk."""
        if self._sessions_path.exists():
            try:
                with open(self._sessions_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.sessions = {
                    s["id"]: Session.from_dict(s) for s in data
                }
            except Exception as e:
                print(f"Error loading sessions: {e}")
                self.sessions = {}
    
    def _save_sessions(self) -> None:
        """Save sessions to disk."""
        self._sessions_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._sessions_path, "w", encoding="utf-8") as f:
            json.dump(
                [s.to_dict() for s in self.sessions.values()],
                f,
                indent=2,
                ensure_ascii=False,
            )
    
    # ──────────────────────────────────────────────────────────
    # Chat Processing
    # ──────────────────────────────────────────────────────────
    
    def process_message(self, session_id: str, user_message: str) -> str:
        """
        Process a user message and return response.
        
        Args:
            session_id: Session ID
            user_message: User's message
            
        Returns:
            Assistant response
        """
        self.initialize()
        
        # Add user message to session
        self.add_message_to_session(session_id, "user", user_message)
        
        # Add to memory STM
        self.memory_manager.add_user_input(user_message)
        
        # Analyze input
        decision = self.decision_layer.analyze(user_message)
        
        # Handle tool decisions
        tool_result = None
        if decision.decision_type == DecisionType.USE_TOOL and decision.tool_call:
            result = self.tool_router.execute(decision.tool_call)
            tool_result = self.tool_router.format_tool_result(
                decision.tool_call.tool_name, result
            )
            self.memory_manager.add_tool_result(tool_result, decision.tool_call.tool_name)
        
        elif decision.decision_type == DecisionType.STORE_MEMORY and decision.memory_content:
            self.memory_manager.store_memory(
                content=decision.memory_content,
                memory_type="fact",
                importance=0.8,
            )
        
        # Get context
        include_ltm = (
            decision.decision_type == DecisionType.RETRIEVE_MEMORY or
            self.decision_layer.should_retrieve_memory(user_message)
        )
        
        memory_context = self.memory_manager.get_context(
            include_ltm=include_ltm,
            ltm_query=decision.memory_query,
        )
        
        # Build context
        tools_description = self.tool_router.get_tools_prompt() if self.config.agent.enable_tools else None
        
        built_context = self.context_builder.build(
            stm_messages=memory_context.stm_messages,
            ltm_memories=memory_context.ltm_memories,
            tools_description=tools_description,
        )
        
        # Generate response
        response = self.llm.chat(
            messages=built_context.messages,
            max_new_tokens=self.config.llm.max_new_tokens,
            temperature=self.config.llm.temperature,
        )
        
        # Clean response
        response = self._clean_response(response)
        
        # Add to STM and session
        self.memory_manager.add_assistant_response(response)
        self.add_message_to_session(session_id, "model", response)
        
        return response
    
    def stream_message(self, session_id: str, user_message: str):
        """
        Stream response for a user message.
        
        Yields response chunks.
        """
        self.initialize()
        
        # Add user message
        self.add_message_to_session(session_id, "user", user_message)
        self.memory_manager.add_user_input(user_message)
        
        # Get context
        include_ltm = self.decision_layer.should_retrieve_memory(user_message)
        memory_context = self.memory_manager.get_context(include_ltm=include_ltm)
        
        tools_description = self.tool_router.get_tools_prompt() if self.config.agent.enable_tools else None
        
        built_context = self.context_builder.build(
            stm_messages=memory_context.stm_messages,
            ltm_memories=memory_context.ltm_memories,
            tools_description=tools_description,
        )
        
        # Stream response
        full_response = ""
        for chunk in self.llm.stream_chat(messages=built_context.messages):
            full_response += chunk
            yield chunk
        
        # Clean and save
        clean_response = self._clean_response(full_response)
        self.memory_manager.add_assistant_response(clean_response)
        self.add_message_to_session(session_id, "model", clean_response)
    
    def _clean_response(self, response: str) -> str:
        """Clean LLM response."""
        import re
        cleaned = re.sub(r'\[TOOL:\s*\w+\([^)]*\)\s*\]', '', response)
        cleaned = "\n".join(line for line in cleaned.split("\n") if line.strip())
        return cleaned.strip()
    
    # ──────────────────────────────────────────────────────────
    # Memory Operations
    # ──────────────────────────────────────────────────────────
    
    def store_memory(
        self,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
    ) -> dict:
        """Store a memory."""
        self.initialize()
        memory = self.memory_manager.store_memory(
            content=content,
            memory_type=memory_type,
            importance=importance,
        )
        return {
            "id": memory.id,
            "content": memory.content,
            "memory_type": memory.memory_type,
            "importance": memory.importance,
            "timestamp": memory.timestamp.isoformat(),
        }
    
    def search_memories(
        self,
        query: str,
        top_k: int = 5,
        memory_type: Optional[str] = None,
    ) -> list[dict]:
        """Search memories."""
        self.initialize()
        results = self.memory_manager.search_memories(
            query=query,
            top_k=top_k,
            memory_type=memory_type,
        )
        return [
            {
                "id": mem.id,
                "content": mem.content,
                "memory_type": mem.memory_type,
                "importance": mem.importance,
                "timestamp": mem.timestamp.isoformat(),
                "similarity": score,
            }
            for mem, score in results
        ]
    
    def get_memory_stats(self) -> dict:
        """Get memory statistics."""
        if not self._initialized:
            return {
                "stm_messages": 0,
                "stm_turns": 0,
                "ltm_memories": 0,
                "total_turns_processed": 0,
            }
        return self.memory_manager.get_stats()
    
    def clear_stm(self) -> None:
        """Clear short-term memory."""
        if self._memory_manager:
            self._memory_manager.clear_stm()
    
    def clear_ltm(self) -> None:
        """Clear long-term memory."""
        if self._memory_manager:
            self._memory_manager.clear_ltm()
    
    # ──────────────────────────────────────────────────────────
    # Tool Operations
    # ──────────────────────────────────────────────────────────
    
    def list_tools(self) -> list[dict]:
        """List available tools."""
        self.initialize()
        return self.tool_router.registry.get_schemas()
    
    def execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool."""
        self.initialize()
        from agent.tool_router import ToolCall
        
        tool_call = ToolCall(tool_name=tool_name, arguments=arguments)
        result = self.tool_router.execute(tool_call)
        
        return {
            "tool_name": tool_name,
            "success": result.is_success,
            "output": str(result.output) if result.output else None,
            "error": result.error,
        }


# Global instance getter
def get_agent_manager(config: Optional[Config] = None) -> AgentManager:
    """Get the global AgentManager instance."""
    return AgentManager.get_instance(config)
