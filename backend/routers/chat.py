"""Chat router — API endpoints for asking questions about indexed codebases."""

import json
import logging

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from backend.models.schemas import ChatRequest, ChatResponse, SourceReference
from backend.services.rag_engine import generate_answer, generate_answer_stream
from backend.services.vector_store import get_or_create_collection

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Ask a question about an indexed codebase.

    Returns the complete answer with source references.
    """
    # Verify repo exists
    try:
        collection = get_or_create_collection(request.repo_id)
        if collection.count() == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Repository '{request.repo_id}' has not been indexed yet.",
            )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        result = await generate_answer(
            repo_id=request.repo_id,
            question=request.question,
            chat_history=request.chat_history,
        )

        sources = [
            SourceReference(**src) for src in result.get("sources", [])
        ]

        return ChatResponse(
            answer=result["answer"],
            sources=sources,
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Ask a question with streaming response via Server-Sent Events (SSE).

    Events:
      - type="sources" → source references (sent first)
      - type="token"   → answer text tokens (streamed)
      - type="done"    → stream complete
    """
    # Verify repo exists
    try:
        collection = get_or_create_collection(request.repo_id)
        if collection.count() == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Repository '{request.repo_id}' has not been indexed yet.",
            )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    async def event_generator():
        try:
            async for chunk in generate_answer_stream(
                repo_id=request.repo_id,
                question=request.question,
                chat_history=request.chat_history,
            ):
                yield {
                    "event": chunk["type"],
                    "data": json.dumps(chunk["content"]) if isinstance(chunk["content"], (list, dict)) else chunk["content"],
                }

            yield {"event": "done", "data": ""}

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())
