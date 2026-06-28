"""Embedding service — generate vector embeddings using Google GenAI SDK."""

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Initialize the new GenAI client
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Embedding model — free tier, 768 dimensions
EMBEDDING_MODEL = "gemini-embedding-001"


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


import time
from google.genai.errors import APIError

def generate_embeddings_batch(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """
    Generate embeddings for multiple texts in batches.
    Includes robust retry logic for 429 RESOURCE_EXHAUSTED errors.
    """
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        
        # Retry loop for this batch
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = _client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
                )
                all_embeddings.extend([emb.values for emb in response.embeddings])
                break # Success, break out of retry loop
            except APIError as e:
                # If we hit a rate limit (429) and haven't exhausted retries, sleep and retry
                if "429" in str(e) and attempt < max_retries - 1:
                    time.sleep(15.0) # Wait 15 seconds before retrying
                    continue
                raise e # Re-raise if it's not a 429 or we ran out of retries
        
        # Add a delay between successful batches to prevent hitting the limit
        if i + batch_size < len(texts):
            time.sleep(5.0)

    return all_embeddings
