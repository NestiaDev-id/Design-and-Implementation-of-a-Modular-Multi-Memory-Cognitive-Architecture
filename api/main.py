"""
Cognitive Memory API - FastAPI Backend

A RESTful API for the Cognitive Memory Agent system.
Provides endpoints for chat, sessions, memory, and tools.

Usage:
    uvicorn api.main:app --reload --port 8000
    
Or:
    python -m api.main
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app.services import chat_router, sessions_router, memory_router, tools_router
from api.app.utils import get_agent_manager
from api.app.models import HealthResponse, MemoryStatsResponse


# ──────────────────────────────────────────────────────────────
# Lifespan Events
# ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting Cognitive Memory API...")
    
    # Initialize agent manager (lazy - will load LLM on first request)
    agent = get_agent_manager()
    print(f"Agent manager initialized. Sessions: {len(agent.sessions)}")
    
    yield
    
    # Shutdown
    print("Shutting down Cognitive Memory API...")


# ──────────────────────────────────────────────────────────────
# FastAPI Application
# ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Cognitive Memory API",
    description="""
API for the Cognitive Memory Agent with Qwen LLM.

Features:
- **Chat**: Send messages and receive AI responses with streaming support
- **Sessions**: Manage chat sessions
- **Memory**: Store and search long-term memories
- **Tools**: Execute tools (calculator, datetime, etc.)
    """,
    version="1.0.0",
    lifespan=lifespan,
)


# ──────────────────────────────────────────────────────────────
# CORS Middleware
# ──────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────
# Include Routers
# ──────────────────────────────────────────────────────────────

app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(memory_router)
app.include_router(tools_router)


# ──────────────────────────────────────────────────────────────
# Root Endpoints
# ──────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "Cognitive Memory API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    agent = get_agent_manager()
    stats = agent.get_memory_stats()
    
    return HealthResponse(
        status="ok",
        llm_loaded=agent.is_llm_loaded,
        memory_stats=MemoryStatsResponse(
            stm_messages=stats.get("stm_messages", 0),
            stm_turns=stats.get("stm_turns", 0),
            ltm_memories=stats.get("ltm_memories", 0),
            total_turns_processed=stats.get("stm_total_turns", 0),
        ),
    )


@app.post("/initialize")
async def initialize_agent():
    """
    Explicitly initialize the agent and load the LLM.
    
    This is optional - the agent will auto-initialize on first chat.
    """
    agent = get_agent_manager()
    
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, agent.initialize)
    
    return {
        "status": "initialized",
        "llm_loaded": agent.is_llm_loaded,
    }


# ──────────────────────────────────────────────────────────────
# Error Handlers
# ──────────────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": str(exc.status_code)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "code": "INTERNAL_ERROR"},
    )


# ──────────────────────────────────────────────────────────────
# Run with Uvicorn
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(Path(__file__).parent.parent)],
    )
