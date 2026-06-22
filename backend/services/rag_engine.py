"""RAG Engine — orchestrates retrieval, augmentation, and generation.

Uses the new google-genai SDK (replaces deprecated google.generativeai).
"""

import os
from collections.abc import AsyncGenerator

from dotenv import load_dotenv
from google import genai
from google.genai import types

from backend.services.vector_store import query_similar

load_dotenv()

# Initialize the new GenAI client
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Use Gemini 2.5 Flash — improved reasoning, thinking mode, free tier available
LLM_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are CodeSage, an expert AI assistant that answers questions about codebases.
You have been given relevant code snippets from a repository to help answer the user's question.

RULES:
1. Answer based ONLY on the provided code context. Do not make up information.
2. Reference specific files and line numbers when relevant (e.g., "In `src/auth.py` lines 42-67...").
3. Include relevant code snippets in your answer using markdown code blocks with the appropriate language.
4. If the context doesn't contain enough information to fully answer, say so clearly.
5. Be concise but thorough. Explain complex code logic in plain English.
6. When discussing multiple files, explain how they relate to each other.
7. Format your answers with markdown for readability."""


def build_context(similar_chunks: list[dict]) -> str:
    """Build the context string from retrieved chunks."""
    context_parts = []
    for i, chunk in enumerate(similar_chunks, 1):
        meta = chunk["metadata"]
        file_path = meta.get("file_path", "unknown")
        start_line = meta.get("start_line", "?")
        end_line = meta.get("end_line", "?")
        score = chunk.get("relevance_score", 0)

        header = f"--- Source {i}: {file_path} (lines {start_line}-{end_line}) [relevance: {score:.2f}] ---"
        context_parts.append(f"{header}\n{chunk['document']}")

    return "\n\n".join(context_parts)


def build_gemini_history(history: list[dict]) -> list[types.Content]:
    """Convert chat history to google-genai Content objects."""
    contents = []
    for msg in history:
        role = "user" if msg.get("role") == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=msg.get("content", ""))])
        )
    return contents


async def generate_answer(
    repo_id: str,
    question: str,
    chat_history: list[dict] | None = None,
    n_context_chunks: int = 8,
) -> dict:
    """
    Full RAG pipeline: retrieve relevant code → augment prompt → generate answer.

    Returns dict with 'answer' and 'sources'.
    """
    # 1. Retrieve relevant code chunks
    similar_chunks = query_similar(repo_id, question, n_results=n_context_chunks)

    if not similar_chunks:
        return {
            "answer": "I haven't indexed any code for this repository yet. Please ingest a repository first.",
            "sources": [],
        }

    # 2. Build context from retrieved chunks
    context = build_context(similar_chunks)

    # 3. Build the augmented prompt
    augmented_prompt = f"""CODEBASE CONTEXT:
{context}

USER QUESTION: {question}

Please answer the question based on the code context provided above."""

    # 4. Build conversation history
    history_contents = build_gemini_history(chat_history) if chat_history else []

    # 5. Generate answer with Gemini
    all_contents = history_contents + [
        types.Content(role="user", parts=[types.Part(text=augmented_prompt)])
    ]

    response = _client.models.generate_content(
        model=LLM_MODEL,
        contents=all_contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
        ),
    )

    # 6. Build source references
    sources = []
    for chunk in similar_chunks:
        meta = chunk["metadata"]
        sources.append({
            "file_path": meta.get("file_path", ""),
            "start_line": meta.get("start_line"),
            "end_line": meta.get("end_line"),
            "snippet": chunk["document"][:200] + "..." if len(chunk["document"]) > 200 else chunk["document"],
            "relevance_score": chunk.get("relevance_score", 0),
        })

    return {
        "answer": response.text,
        "sources": sources,
    }


async def generate_answer_stream(
    repo_id: str,
    question: str,
    chat_history: list[dict] | None = None,
    n_context_chunks: int = 8,
) -> AsyncGenerator[dict, None]:
    """
    Streaming RAG pipeline — yields answer tokens as they're generated.

    Yields dicts with either:
      - {"type": "token", "content": "..."} for answer tokens
      - {"type": "sources", "content": [...]} for source references
    """
    # 1. Retrieve relevant code chunks
    similar_chunks = query_similar(repo_id, question, n_results=n_context_chunks)

    if not similar_chunks:
        yield {"type": "token", "content": "I haven't indexed any code for this repository yet."}
        return

    # Yield sources first so frontend can display them while streaming begins
    sources = []
    for chunk in similar_chunks:
        meta = chunk["metadata"]
        sources.append({
            "file_path": meta.get("file_path", ""),
            "start_line": meta.get("start_line"),
            "end_line": meta.get("end_line"),
            "relevance_score": chunk.get("relevance_score", 0),
        })
    yield {"type": "sources", "content": sources}

    # 2. Build context and prompt
    context = build_context(similar_chunks)
    augmented_prompt = f"""CODEBASE CONTEXT:
{context}

USER QUESTION: {question}

Please answer the question based on the code context provided above."""

    # 3. Build conversation history
    history_contents = build_gemini_history(chat_history) if chat_history else []
    all_contents = history_contents + [
        types.Content(role="user", parts=[types.Part(text=augmented_prompt)])
    ]

    # 4. Stream response from Gemini
    for chunk in _client.models.generate_content_stream(
        model=LLM_MODEL,
        contents=all_contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
        ),
    ):
        if chunk.text:
            yield {"type": "token", "content": chunk.text}


async def explain_file(
    repo_id: str,
    file_path: str,
    file_content: str,
) -> AsyncGenerator[dict, None]:
    """
    'Explain this file' mode — streams a comprehensive AI explanation of a single file.

    Yields {"type": "token", "content": "..."} tokens.
    """
    prompt = f"""Please provide a comprehensive explanation of this file from the codebase.

FILE: {file_path}

CONTENT:
```
{file_content[:8000]}  # limit to 8k chars
```

Include:
1. **Purpose** — What does this file do?
2. **Key Components** — Describe each class, function, or important block.
3. **Dependencies** — What does it import/depend on?
4. **How It Fits** — How does it relate to the rest of the codebase?
5. **Notable Patterns** — Any interesting design patterns or techniques used."""

    for chunk in _client.models.generate_content_stream(
        model=LLM_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
        ),
    ):
        if chunk.text:
            yield {"type": "token", "content": chunk.text}
