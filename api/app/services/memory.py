"""Memory API routes."""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import asyncio

from ..models.schemas import (
    MemoryStoreRequest,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryItem,
    MemoryStatsResponse,
)
from ..utils.agent_manager import get_agent_manager

router = APIRouter(prefix="/memory", tags=["Memory"])


@router.post("/store", response_model=MemoryItem)
async def store_memory(request: MemoryStoreRequest):
    """Store a memory in long-term memory."""
    agent = get_agent_manager()
    
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: agent.store_memory(
                content=request.content,
                memory_type=request.memory_type.value,
                importance=request.importance,
            ),
        )
        
        return MemoryItem(
            id=result["id"],
            content=result["content"],
            memory_type=result["memory_type"],
            importance=result["importance"],
            timestamp=datetime.fromisoformat(result["timestamp"]),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=MemorySearchResponse)
async def search_memories(request: MemorySearchRequest):
    """Search long-term memory."""
    agent = get_agent_manager()
    
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: agent.search_memories(
                query=request.query,
                top_k=request.top_k,
                memory_type=request.memory_type.value if request.memory_type else None,
            ),
        )
        
        return MemorySearchResponse(
            results=[
                MemoryItem(
                    id=r["id"],
                    content=r["content"],
                    memory_type=r["memory_type"],
                    importance=r["importance"],
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    similarity=r.get("similarity"),
                )
                for r in results
            ],
            query=request.query,
            total=len(results),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=MemoryStatsResponse)
async def get_memory_stats():
    """Get memory statistics."""
    agent = get_agent_manager()
    stats = agent.get_memory_stats()
    
    return MemoryStatsResponse(
        stm_messages=stats.get("stm_messages", 0),
        stm_turns=stats.get("stm_turns", 0),
        ltm_memories=stats.get("ltm_memories", 0),
        total_turns_processed=stats.get("stm_total_turns", 0),
    )


@router.post("/clear/stm")
async def clear_stm():
    """Clear short-term memory."""
    agent = get_agent_manager()
    agent.clear_stm()
    return {"message": "Short-term memory cleared"}


@router.post("/clear/ltm")
async def clear_ltm():
    """Clear long-term memory."""
    agent = get_agent_manager()
    agent.clear_ltm()
    return {"message": "Long-term memory cleared"}


@router.post("/clear/all")
async def clear_all_memory():
    """Clear all memory (STM + LTM)."""
    agent = get_agent_manager()
    agent.clear_stm()
    agent.clear_ltm()
    return {"message": "All memory cleared"}
