"""Ingest router — API endpoints for cloning and indexing repositories."""

import json
import logging
import shutil
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from backend.models.schemas import IngestRequest, IngestResponse, RepoInfo, RepoListResponse
from backend.services.chunker import chunk_file
from backend.services.embedder import generate_embeddings_batch
from backend.services.repo_loader import REPOS_DIR, clone_repo, get_repo_name, load_files
from backend.services.vector_store import delete_collection, store_chunks

logger = logging.getLogger(__name__)
router = APIRouter()


def _save_repo_meta(repo_id: str, meta: dict) -> None:
    """Persist repo metadata to disk so it survives server restarts."""
    meta_path = REPOS_DIR / repo_id / ".codesage_meta.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")


def _load_repo_meta(repo_id: str) -> dict | None:
    """Load repo metadata from disk."""
    meta_path = REPOS_DIR / repo_id / ".codesage_meta.json"
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None


@router.post("/ingest", response_model=IngestResponse)
async def ingest_repo(request: IngestRequest):
    """
    Clone a GitHub repository, chunk the code, generate embeddings,
    and store everything in ChromaDB for later querying.
    """
    repo_url = str(request.repo_url)
    repo_name = get_repo_name(repo_url)

    try:
        # 1. Clone the repository
        logger.info(f"Cloning repository: {repo_url}")
        repo_id, repo_path = clone_repo(repo_url, request.branch, request.github_token)

        # 2. Load all code files
        logger.info(f"Loading files from {repo_path}")
        files = load_files(repo_path)

        if not files:
            raise HTTPException(
                status_code=400,
                detail="No indexable code files found in the repository.",
            )

        # 3. Chunk all files
        logger.info(f"Chunking {len(files)} files")
        all_chunks = []
        for file_info in files:
            file_chunks = chunk_file(file_info["content"], file_info["path"])
            all_chunks.extend(file_chunks)

        # 4. Generate embeddings for all chunks
        logger.info(f"Generating embeddings for {len(all_chunks)} chunks")
        documents = [chunk.to_document() for chunk in all_chunks]
        embeddings = generate_embeddings_batch(documents)

        # 5. Store in ChromaDB
        logger.info(f"Storing {len(all_chunks)} chunks in ChromaDB")
        chromadb_chunks = []
        for chunk, embedding in zip(all_chunks, embeddings):
            chromadb_chunks.append({
                "id": chunk.id,
                "document": chunk.to_document(),
                "embedding": embedding,
                "metadata": {
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "chunk_type": chunk.chunk_type,
                    "name": chunk.name,
                },
            })

        chunks_stored = store_chunks(repo_id, chromadb_chunks)

        # 6. Persist metadata to disk (survives restarts)
        meta = {
            "repo_id": repo_id,
            "repo_name": repo_name,
            "repo_url": repo_url,
            "files_indexed": len(files),
            "chunks_created": chunks_stored,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_repo_meta(repo_id, meta)

        logger.info(f"Successfully indexed {repo_name}: {len(files)} files, {chunks_stored} chunks")

        return IngestResponse(
            repo_id=repo_id,
            repo_name=repo_name,
            files_indexed=len(files),
            chunks_created=chunks_stored,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to ingest repository: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to ingest repository: {str(e)}")


@router.get("/repos", response_model=RepoListResponse)
async def list_repos():
    """List all indexed repositories (persisted to disk)."""
    if not REPOS_DIR.exists():
        return RepoListResponse(repos=[])

    repos = []
    for path in REPOS_DIR.iterdir():
        if path.is_dir():
            meta = _load_repo_meta(path.name)
            if meta:
                # repo_url may not exist in older meta files
                meta.setdefault("repo_url", "")
                repos.append(RepoInfo(**meta))

    repos.sort(key=lambda r: r.indexed_at, reverse=True)
    return RepoListResponse(repos=repos)


@router.delete("/repos/{repo_id}")
async def delete_repo(repo_id: str):
    """Delete an indexed repository and its embeddings."""
    repo_path = REPOS_DIR / repo_id
    delete_collection(repo_id)
    if repo_path.exists():
        shutil.rmtree(repo_path)
    return {"status": "deleted", "repo_id": repo_id}
