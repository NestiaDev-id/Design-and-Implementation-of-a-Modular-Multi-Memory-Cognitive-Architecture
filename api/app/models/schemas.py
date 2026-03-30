"""Pydantic schemas for API request/response models."""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


# ─────────────────────────────────────────────────────────────
# Message & Chat Schemas
# ─────────────────────────────────────────────────────────────

class MessageRole(str, Enum):
    """Message role enum."""
    USER = "user"
    MODEL = "model"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class MessageBase(BaseModel):
    """Base message schema."""
    role: MessageRole
    content: str


class MessageCreate(MessageBase):
    """Message creation schema."""
    pass


class MessageResponse(MessageBase):
    """Message response schema."""
    id: str
    timestamp: datetime
    is_streaming: bool = False
    
    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """Chat request schema."""
    session_id: str
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123",
                "message": "Hello, how are you?"
            }
        }


class ChatResponse(BaseModel):
    """Chat response schema (non-streaming)."""
    session_id: str
    message_id: str
    role: MessageRole = MessageRole.MODEL
    content: str
    timestamp: datetime
    tool_used: Optional[str] = None
    
    class Config:
        from_attributes = True


class RegenerateRequest(BaseModel):
    """Regenerate request schema."""
    session_id: str
    message_id: str


# ─────────────────────────────────────────────────────────────
# Session Schemas
# ─────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    """Session creation schema."""
    title: Optional[str] = "New Chat"


class SessionResponse(BaseModel):
    """Session response schema."""
    id: str
    title: str
    message_count: int = 0
    updated_at: datetime
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """Session list response."""
    sessions: list[SessionResponse]
    total: int


class SessionDetailResponse(SessionResponse):
    """Session with messages."""
    messages: list[MessageResponse] = []


# ─────────────────────────────────────────────────────────────
# Memory Schemas
# ─────────────────────────────────────────────────────────────

class MemoryType(str, Enum):
    """Memory type enum."""
    FACT = "fact"
    PREFERENCE = "preference"
    TASK = "task"
    CONVERSATION = "conversation"


class MemoryStoreRequest(BaseModel):
    """Memory store request."""
    content: str
    memory_type: MemoryType = MemoryType.FACT
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "User's name is John",
                "memory_type": "fact",
                "importance": 0.8
            }
        }


class MemorySearchRequest(BaseModel):
    """Memory search request."""
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    memory_type: Optional[MemoryType] = None


class MemoryItem(BaseModel):
    """Memory item response."""
    id: str
    content: str
    memory_type: str
    importance: float
    timestamp: datetime
    similarity: Optional[float] = None


class MemorySearchResponse(BaseModel):
    """Memory search response."""
    results: list[MemoryItem]
    query: str
    total: int


class MemoryStatsResponse(BaseModel):
    """Memory statistics response."""
    stm_messages: int
    stm_turns: int
    ltm_memories: int
    total_turns_processed: int


# ─────────────────────────────────────────────────────────────
# Tool Schemas
# ─────────────────────────────────────────────────────────────

class ToolRequest(BaseModel):
    """Tool execution request."""
    tool_name: str
    arguments: dict = Field(default_factory=dict)


class ToolResponse(BaseModel):
    """Tool execution response."""
    tool_name: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None


class ToolListResponse(BaseModel):
    """List of available tools."""
    tools: list[dict]


# ─────────────────────────────────────────────────────────────
# System Schemas
# ─────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    llm_loaded: bool
    memory_stats: MemoryStatsResponse


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
