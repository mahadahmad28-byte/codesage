"""Repos router — list all indexed repositories and delete them."""

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.models.schemas import RepoInfo, RepoListResponse
from backend.services.repo_loader import REPOS_DIR

logger = logging.getLogger(__name__)
router = APIRouter()


def _load_repo_meta(repo_path: Path) -> RepoInfo | None:
    """Load metadata for an indexed repo from its meta.json file."""
    meta_file = repo_path / ".codesage_meta.json"
    if not meta_file.exists():
        return None
    try:
        data = json.loads(meta_file.read_text(encoding="utf-8"))
        return RepoInfo(**data)
    except Exception:
        return None


@router.get("/repos", response_model=RepoListResponse)
async def list_repos():
    """List all indexed repositories."""
    if not REPOS_DIR.exists():
        return RepoListResponse(repos=[])

    repos = []
    for path in REPOS_DIR.iterdir():
        if path.is_dir():
            info = _load_repo_meta(path)
            if info:
                repos.append(info)

    # Sort by indexed_at descending (newest first)
    repos.sort(key=lambda r: r.indexed_at, reverse=True)
    return RepoListResponse(repos=repos)


@router.delete("/repos/{repo_id}")
async def delete_repo(repo_id: str):
    """Delete an indexed repository and its vector data."""
    import shutil

    from backend.services.vector_store import delete_collection

    repo_path = REPOS_DIR / repo_id
    if not repo_path.exists():
        raise HTTPException(status_code=404, detail=f"Repo '{repo_id}' not found")

    try:
        # Remove cloned repo files
        shutil.rmtree(repo_path)
        # Remove ChromaDB collection
        delete_collection(repo_id)
        return {"status": "deleted", "repo_id": repo_id}
    except Exception as e:
        logger.error(f"Failed to delete repo {repo_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
