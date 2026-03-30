"""Session API routes."""

from fastapi import APIRouter, HTTPException
from datetime import datetime

from ..models.schemas import (
    SessionCreate,
    SessionResponse,
    SessionListResponse,
    SessionDetailResponse,
    MessageResponse,
    MessageRole,
)
from ..utils.agent_manager import get_agent_manager

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("/", response_model=SessionListResponse)
async def list_sessions():
    """List all chat sessions."""
    agent = get_agent_manager()
    sessions = agent.list_sessions()
    
    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=s.id,
                title=s.title,
                message_count=len(s.messages),
                updated_at=s.updated_at,
                created_at=s.created_at,
            )
            for s in sessions
        ],
        total=len(sessions),
    )


@router.post("/", response_model=SessionResponse)
async def create_session(request: SessionCreate):
    """Create a new chat session."""
    agent = get_agent_manager()
    session = agent.create_session(title=request.title or "New Chat")
    
    return SessionResponse(
        id=session.id,
        title=session.title,
        message_count=0,
        updated_at=session.updated_at,
        created_at=session.created_at,
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str):
    """Get a specific session with messages."""
    agent = get_agent_manager()
    session = agent.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        message_count=len(session.messages),
        updated_at=session.updated_at,
        created_at=session.created_at,
        messages=[
            MessageResponse(
                id=m["id"],
                role=MessageRole(m["role"]) if m["role"] in ["user", "model", "assistant"] else MessageRole.MODEL,
                content=m["content"],
                timestamp=datetime.fromisoformat(m["timestamp"]),
            )
            for m in session.messages
        ],
    )


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Delete a chat session."""
    agent = get_agent_manager()
    
    if not agent.get_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    
    agent.delete_session(session_id)
    
    return {"message": "Session deleted", "session_id": session_id}


@router.patch("/{session_id}/title")
async def update_session_title(session_id: str, title: str):
    """Update session title."""
    agent = get_agent_manager()
    
    session = agent.update_session_title(session_id, title)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionResponse(
        id=session.id,
        title=session.title,
        message_count=len(session.messages),
        updated_at=session.updated_at,
        created_at=session.created_at,
    )


@router.delete("/{session_id}/messages/{message_id}")
async def delete_message(session_id: str, message_id: str):
    """Delete a specific message from a session."""
    agent = get_agent_manager()
    
    session = agent.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Find and remove message
    original_count = len(session.messages)
    session.messages = [m for m in session.messages if m["id"] != message_id]
    
    if len(session.messages) == original_count:
        raise HTTPException(status_code=404, detail="Message not found")
    
    session.updated_at = datetime.now()
    agent._save_sessions()
    
    return {"message": "Message deleted", "message_id": message_id}
