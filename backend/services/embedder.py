"""Embedding service — generate vector embeddings using Google GenAI SDK."""

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Initialize the new GenAI client
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Embedding model — free tier, 768 dimensions
EMBEDDING_MODEL = "text-embedding-004"


def generate_embedding(text: str) -> list[float]:
    """
    Generate a single embedding vector for the given text.

    Uses Gemini text-embedding-004 (free tier, 768 dimensions).
    """
    response = _client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return response.embeddings[0].values


def generate_query_embedding(query: str) -> list[float]:
    """
    Generate an embedding optimized for search queries.

    Uses RETRIEVAL_QUERY task type for better search relevance.
    """
    response = _client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return response.embeddings[0].values


def generate_embeddings_batch(texts: list[str], batch_size: int = 20) -> list[list[float]]:
    """
    Generate embeddings for multiple texts in batches.

    Gemini free tier has rate limits (1500 RPD / 100 QPM),
    so we process in small batches.
    """
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = _client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        all_embeddings.extend([emb.values for emb in response.embeddings])

    return all_embeddings
