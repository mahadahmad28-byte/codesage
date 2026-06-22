"""Repository loading service — clone repos and extract code files."""

import hashlib
import os
import shutil
from pathlib import Path

from git import Repo

REPOS_DIR = Path(os.getenv("REPOS_DIR", "./repos"))

# File extensions to index (code files only)
INDEXABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h",
    ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".cs", ".scala",
    ".html", ".css", ".scss", ".sql", ".sh", ".bash", ".yaml", ".yml",
    ".json", ".toml", ".xml", ".md", ".txt", ".r", ".dart", ".vue",
    ".svelte", ".ex", ".exs", ".zig", ".lua",
}

# Directories to always skip
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    ".idea", ".vscode", "dist", "build", ".next", ".nuxt",
    "vendor", "target", ".gradle", "coverage", ".pytest_cache",
    ".tox", "eggs", ".eggs", "*.egg-info",
}

# Max file size to index (500KB)
MAX_FILE_SIZE = 500 * 1024


def generate_repo_id(repo_url: str) -> str:
    """Generate a deterministic ID for a repo URL."""
    return hashlib.sha256(repo_url.encode()).hexdigest()[:12]


def clone_repo(repo_url: str, branch: str = "main", github_token: str | None = None) -> tuple[str, Path]:
    """
    Clone a GitHub repository and return (repo_id, local_path).

    If the repo is already cloned, pulls latest changes instead.
    For private repos, supply a github_token — it will be injected into
    the HTTPS URL as: https://<token>@github.com/user/repo
    """
    repo_id = generate_repo_id(repo_url)
    local_path = REPOS_DIR / repo_id

    REPOS_DIR.mkdir(parents=True, exist_ok=True)

    # Build authenticated URL if token provided
    clone_url = repo_url
    if github_token:
        # Convert https://github.com/user/repo → https://<token>@github.com/user/repo
        clone_url = repo_url.replace("https://", f"https://{github_token}@", 1)

    if local_path.exists():
        # Pull latest changes
        try:
            repo = Repo(local_path)
            # Update remote URL with (possibly new) token
            repo.remotes.origin.set_url(clone_url)
            repo.remotes.origin.pull(branch)
        except Exception:
            # If pull fails, re-clone
            shutil.rmtree(local_path)
            Repo.clone_from(clone_url, local_path, branch=branch, depth=1)
    else:
        # Fresh clone (shallow for speed)
        Repo.clone_from(clone_url, local_path, branch=branch, depth=1)

    return repo_id, local_path


def get_repo_name(repo_url: str) -> str:
    """Extract repository name from URL."""
    # Handle URLs like https://github.com/user/repo or https://github.com/user/repo.git
    name = repo_url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name


def load_files(repo_path: Path) -> list[dict]:
    """
    Walk the repo directory and load all indexable code files.

    Returns a list of dicts with 'path' (relative), 'content', and 'size'.
    """
    files = []

    for file_path in repo_path.rglob("*"):
        # Skip directories in the skip list
        if any(skip_dir in file_path.parts for skip_dir in SKIP_DIRS):
            continue

        # Skip non-files
        if not file_path.is_file():
            continue

        # Skip non-indexable extensions
        if file_path.suffix.lower() not in INDEXABLE_EXTENSIONS:
            continue

        # Skip large files
        if file_path.stat().st_size > MAX_FILE_SIZE:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if content.strip():  # Skip empty files
                relative_path = str(file_path.relative_to(repo_path))
                files.append({
                    "path": relative_path,
                    "content": content,
                    "size": len(content),
                })
        except (UnicodeDecodeError, PermissionError):
            continue

    return files


def get_file_tree(repo_path: Path) -> dict:
    """
    Build a nested file tree structure for the repository.

    Returns a dict representing the tree with name, path, is_directory, children.
    """

    def build_node(path: Path, relative_to: Path) -> dict | None:
        rel_path = str(path.relative_to(relative_to))
        name = path.name

        if path.is_dir():
            # Skip excluded directories
            if name in SKIP_DIRS:
                return None

            children = []
            try:
                for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                    child_node = build_node(child, relative_to)
                    if child_node is not None:
                        children.append(child_node)
            except PermissionError:
                pass

            return {
                "name": name,
                "path": rel_path,
                "is_directory": True,
                "children": children,
            }
        else:
            if path.suffix.lower() not in INDEXABLE_EXTENSIONS:
                return None
            return {
                "name": name,
                "path": rel_path,
                "is_directory": False,
                "children": [],
                "size": path.stat().st_size,
            }

    root = build_node(repo_path, repo_path)
    if root:
        root["name"] = repo_path.name
        root["path"] = "."
    return root
