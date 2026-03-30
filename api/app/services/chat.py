"""Chat API routes with SSE streaming support."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json
import asyncio

from ..models.schemas import (
    ChatRequest,
    ChatResponse,
    RegenerateRequest,
    MessageRole,
    ErrorResponse,
)
from ..utils.agent_manager import get_agent_manager

router = APIRouter(prefix="/chat", tags=["Chat"])


async def generate_sse_stream(session_id: str, message: str) -> AsyncGenerator[str, None]:
    """Generate SSE stream for chat response."""
    agent = get_agent_manager()
    
    try:
        # Run streaming in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        # For now, use non-streaming with chunked output simulation
        # Real streaming would require async generator support in LLM
        response = await loop.run_in_executor(
            None,
            agent.process_message,
            session_id,
            message,
        )
        
        # Send response in chunks
        chunk_size = 20
        for i in range(0, len(response), chunk_size):
            chunk = response[i:i + chunk_size]
            data = {
                "content": chunk,
                "done": i + chunk_size >= len(response),
            }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(0.02)  # Small delay for streaming effect
        
        # Final done message
        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
        
    except Exception as e:
        error_data = {"error": str(e), "done": True}
        yield f"data: {json.dumps(error_data)}\n\n"


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a chat message and get a response.
    
    This endpoint processes the message synchronously.
    For streaming, use /chat/stream.
    """
    agent = get_agent_manager()
    
    # Ensure session exists
    session = agent.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Process message in thread pool
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            agent.process_message,
            request.session_id,
            request.message,
        )
        
        # Get the last message from session
        session = agent.get_session(request.session_id)
        last_message = session.messages[-1] if session.messages else None
        
        from datetime import datetime
        
        return ChatResponse(
            session_id=request.session_id,
            message_id=last_message["id"] if last_message else "",
            role=MessageRole.MODEL,
            content=response,
            timestamp=datetime.now(),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Send a chat message and stream the response via SSE.
    
    Returns a text/event-stream response with chunks.
    """
    agent = get_agent_manager()
    
    # Ensure session exists
    session = agent.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return StreamingResponse(
        generate_sse_stream(request.session_id, request.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/regenerate", response_model=ChatResponse)
async def regenerate(request: RegenerateRequest):
    """
    Regenerate a response for a message.
    
    Removes the message and all following messages, then regenerates.
    """
    agent = get_agent_manager()
    
    session = agent.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Find message index
    msg_index = -1
    for i, msg in enumerate(session.messages):
        if msg["id"] == request.message_id:
            msg_index = i
            break
    
    if msg_index == -1:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Get the user message before this one
    if msg_index == 0:
        raise HTTPException(status_code=400, detail="Cannot regenerate first message")
    
    # Find the last user message before this
    user_message = None
    for i in range(msg_index - 1, -1, -1):
        if session.messages[i]["role"] == "user":
            user_message = session.messages[i]["content"]
            break
    
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found to regenerate from")
    
    # Remove messages from msg_index onwards
    session.messages = session.messages[:msg_index]
    agent._save_sessions()
    
    # Clear STM and re-add messages
    agent.clear_stm()
    for msg in session.messages:
        if msg["role"] == "user":
            agent.memory_manager.add_user_input(msg["content"])
        elif msg["role"] in ["model", "assistant"]:
            agent.memory_manager.add_assistant_response(msg["content"])
    
    # Generate new response
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            agent.process_message,
            request.session_id,
            user_message,
        )
        
        session = agent.get_session(request.session_id)
        last_message = session.messages[-1] if session.messages else None
        
        from datetime import datetime
        
        return ChatResponse(
            session_id=request.session_id,
            message_id=last_message["id"] if last_message else "",
            role=MessageRole.MODEL,
            content=response,
            timestamp=datetime.now(),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
