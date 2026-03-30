"""Tools API routes."""

from fastapi import APIRouter, HTTPException
import asyncio

from ..models.schemas import (
    ToolRequest,
    ToolResponse,
    ToolListResponse,
)
from ..utils.agent_manager import get_agent_manager

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.get("/", response_model=ToolListResponse)
async def list_tools():
    """List all available tools."""
    agent = get_agent_manager()
    
    try:
        tools = agent.list_tools()
        return ToolListResponse(tools=tools)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=ToolResponse)
async def execute_tool(request: ToolRequest):
    """Execute a specific tool with arguments."""
    agent = get_agent_manager()
    
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: agent.execute_tool(
                tool_name=request.tool_name,
                arguments=request.arguments,
            ),
        )
        
        return ToolResponse(
            tool_name=result["tool_name"],
            success=result["success"],
            output=result.get("output"),
            error=result.get("error"),
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
