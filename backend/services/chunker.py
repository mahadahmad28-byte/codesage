"""Code chunking service — split source code into meaningful chunks."""

import re
from dataclasses import dataclass, field


@dataclass
class CodeChunk:
    """A chunk of source code with metadata."""
    content: str
    file_path: str
    start_line: int
    end_line: int
    chunk_type: str = "code"  # "function", "class", "module", "code"
    name: str = ""  # Function/class name if applicable
    metadata: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        """Generate a unique ID for this chunk."""
        return f"{self.file_path}:{self.start_line}-{self.end_line}"

    def to_document(self) -> str:
        """Format chunk as a document string for embedding."""
        header = f"File: {self.file_path} (lines {self.start_line}-{self.end_line})"
        if self.name:
            header += f" | {self.chunk_type}: {self.name}"
        return f"{header}\n\n{self.content}"


# ──────────────────────────────────────────────
# Simple Chunker (Works for all languages)
# ──────────────────────────────────────────────

def chunk_by_lines(
    content: str,
    file_path: str,
    chunk_size: int = 60,
    chunk_overlap: int = 10,
) -> list[CodeChunk]:
    """
    Split code into fixed-size line chunks with overlap.
    Simple but effective — works for any language.
    """
    lines = content.split("\n")
    chunks = []

    if len(lines) <= chunk_size:
        # Small file — keep as one chunk
        chunks.append(CodeChunk(
            content=content,
            file_path=file_path,
            start_line=1,
            end_line=len(lines),
            chunk_type="module",
        ))
        return chunks

    start = 0
    while start < len(lines):
        end = min(start + chunk_size, len(lines))
        chunk_lines = lines[start:end]
        chunk_content = "\n".join(chunk_lines)

        if chunk_content.strip():  # Skip empty chunks
            chunks.append(CodeChunk(
                content=chunk_content,
                file_path=file_path,
                start_line=start + 1,
                end_line=end,
                chunk_type="code",
            ))

        start += chunk_size - chunk_overlap

    return chunks


# ──────────────────────────────────────────────
# Smart Chunker (Python-aware, detects functions/classes)
# ──────────────────────────────────────────────

# Regex patterns for detecting code boundaries
PYTHON_PATTERNS = {
    "class": re.compile(r"^class\s+(\w+)"),
    "function": re.compile(r"^(?:async\s+)?def\s+(\w+)"),
}

JS_TS_PATTERNS = {
    "function": re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)"),
    "class": re.compile(r"^(?:export\s+)?class\s+(\w+)"),
    "arrow": re.compile(r"^(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\("),
}


def chunk_python_smart(content: str, file_path: str) -> list[CodeChunk]:
    """
    Smart chunking for Python files — splits by function/class definitions.
    Falls back to line-based chunking for non-Python or on failure.
    """
    lines = content.split("\n")
    chunks = []
    current_block: list[str] = []
    current_start = 0
    current_name = ""
    current_type = "code"

    def flush_block():
        if current_block:
            block_content = "\n".join(current_block)
            if block_content.strip():
                chunks.append(CodeChunk(
                    content=block_content,
                    file_path=file_path,
                    start_line=current_start + 1,
                    end_line=current_start + len(current_block),
                    chunk_type=current_type,
                    name=current_name,
                ))

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check if this line starts a new function or class (top-level only)
        is_boundary = False
        if not line.startswith((" ", "\t")) and stripped:
            for pattern_type, pattern in PYTHON_PATTERNS.items():
                match = pattern.match(stripped)
                if match:
                    flush_block()
                    current_block = [line]
                    current_start = i
                    current_name = match.group(1)
                    current_type = pattern_type
                    is_boundary = True
                    break

        if not is_boundary:
            current_block.append(line)

    flush_block()

    # If smart chunking produced too few chunks, fall back to line-based
    if len(chunks) <= 1:
        return chunk_by_lines(content, file_path)

    # Further split any very large chunks
    result = []
    for chunk in chunks:
        if chunk.content.count("\n") > 80:
            result.extend(chunk_by_lines(chunk.content, chunk.file_path))
        else:
            result.append(chunk)

    return result


def chunk_file(content: str, file_path: str) -> list[CodeChunk]:
    """
    Chunk a code file using the best strategy for its language.
    """
    if file_path.endswith(".py"):
        return chunk_python_smart(content, file_path)
    else:
        # For all other languages, use line-based chunking
        return chunk_by_lines(content, file_path)
