"""Pydantic models for CodeSage API requests and responses."""

from pydantic import BaseModel, Field, HttpUrl

# ──────────────────────────────────────────────
# Ingest (Repo Indexing)
# ──────────────────────────────────────────────

class IngestRequest(BaseModel):
    """Request to index a GitHub repository."""
    repo_url: HttpUrl = Field(
        ...,
        description="GitHub repository URL to clone and index",
        examples=["https://github.com/user/repo"],
    )
    branch: str = Field(
        default="main",
        description="Branch to clone",
    )
    github_token: str | None = Field(
        default=None,
        description="Personal access token for private repositories",
    )


class IngestResponse(BaseModel):
    """Response after indexing a repository."""
    repo_id: str = Field(..., description="Unique identifier for the indexed repo")
    repo_name: str = Field(..., description="Name of the repository")
    files_indexed: int = Field(..., description="Number of files processed")
    chunks_created: int = Field(..., description="Number of code chunks created")
    status: str = Field(default="success")


# ──────────────────────────────────────────────
# Chat (Q&A)
# ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request to ask a question about an indexed codebase."""
    repo_id: str = Field(..., description="ID of the indexed repository")
    question: str = Field(
        ...,
        description="Natural language question about the codebase",
        min_length=1,
        max_length=2000,
    )
    chat_history: list[dict] = Field(
        default_factory=list,
        description="Previous conversation messages for context",
    )


class ChatResponse(BaseModel):
    """Response to a codebase question."""
    answer: str = Field(..., description="AI-generated answer")
    sources: list["SourceReference"] = Field(
        default_factory=list,
        description="Source code references used to generate the answer",
    )


class SourceReference(BaseModel):
    """A reference to a specific location in the codebase."""
    file_path: str = Field(..., description="Path to the source file")
    start_line: int | None = Field(default=None, description="Start line number")
    end_line: int | None = Field(default=None, description="End line number")
    snippet: str = Field(default="", description="Relevant code snippet")
    relevance_score: float = Field(default=0.0, description="Similarity score (0-1)")


# ──────────────────────────────────────────────
# File Tree
# ──────────────────────────────────────────────

class FileNode(BaseModel):
    """A node in the repository file tree."""
    name: str
    path: str
    is_directory: bool
    children: list["FileNode"] = Field(default_factory=list)
    size: int | None = None  # bytes, for files only


class FileTreeResponse(BaseModel):
    """Response containing the repository file tree."""
    repo_id: str
    repo_name: str
    tree: FileNode


# ──────────────────────────────────────────────
# Repo Listing
# ──────────────────────────────────────────────

class RepoInfo(BaseModel):
    """Summary info about an indexed repository."""
    repo_id: str
    repo_name: str
    repo_url: str = ""
    files_indexed: int
    chunks_created: int
    indexed_at: str


class RepoListResponse(BaseModel):
    """Response listing all indexed repositories."""
    repos: list[RepoInfo] = Field(default_factory=list)
