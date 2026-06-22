"""Explain router — 'Explain this file' streaming endpoint."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.services.rag_engine import explain_file
from backend.services.repo_loader import REPOS_DIR

logger = logging.getLogger(__name__)
router = APIRouter()


class ExplainRequest(BaseModel):
    repo_id: str
    file_path: str


@router.post("/explain")
async def explain_file_endpoint(req: ExplainRequest):
    """
    Stream an AI explanation of a specific file in an indexed repository.
    Sends SSE tokens for real-time display.
    """
    repo_path = REPOS_DIR / req.repo_id
    if not repo_path.exists():
        raise HTTPException(status_code=404, detail="Repository not found")

    # Resolve file path safely (prevent path traversal)
    target = (repo_path / req.file_path).resolve()
    if not str(target).startswith(str(repo_path.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {req.file_path}")

    try:
        file_content = target.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not read file: {e}")

    async def event_stream():
        try:
            async for event in explain_file(req.repo_id, req.file_path, file_content):
                if event["type"] == "token":
                    yield f"data: {event['content']}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Explain stream error: {e}")
            yield f"data: ❌ Error: {e}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
