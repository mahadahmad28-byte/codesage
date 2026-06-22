"""File tree router — API endpoint for fetching a repo's file structure."""

import logging

from fastapi import APIRouter, HTTPException

from backend.models.schemas import FileNode, FileTreeResponse
from backend.services.repo_loader import REPOS_DIR, get_file_tree

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/repos/{repo_id}/tree", response_model=FileTreeResponse)
async def get_repo_tree(repo_id: str):
    """
    Return the file tree for an indexed repository.
    Used by the frontend FileTree sidebar component.
    """
    repo_path = REPOS_DIR / repo_id

    if not repo_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{repo_id}' not found. Index it first via /api/ingest",
        )

    try:
        raw_tree = get_file_tree(repo_path)
        if raw_tree is None:
            raise HTTPException(status_code=404, detail="Could not build file tree")

        def to_node(raw: dict) -> FileNode:
            return FileNode(
                name=raw["name"],
                path=raw["path"],
                is_directory=raw["is_directory"],
                size=raw.get("size"),
                children=[to_node(c) for c in raw.get("children", [])],
            )

        tree_node = to_node(raw_tree)
        repo_name = repo_path.name  # fallback name

        return FileTreeResponse(
            repo_id=repo_id,
            repo_name=repo_name,
            tree=tree_node,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File tree error for {repo_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
