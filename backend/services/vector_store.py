"""Vector store service — ChromaDB wrapper for storing and querying code embeddings."""

import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv

from backend.services.embedder import generate_query_embedding

load_dotenv()

CHROMA_PERSIST_DIR = Path(os.getenv("CHROMA_PERSIST_DIR", "./chroma_data"))


def get_chroma_client() -> chromadb.ClientAPI:
    """Get or create a persistent ChromaDB client."""
    CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))


def get_or_create_collection(repo_id: str) -> chromadb.Collection:
    """Get or create a ChromaDB collection for a repository."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=f"repo_{repo_id}",
        metadata={"hnsw:space": "cosine"},  # Use cosine similarity
    )


def store_chunks(repo_id: str, chunks: list[dict]) -> int:
    """
    Store code chunks with their embeddings in ChromaDB.

    Args:
        repo_id: Unique identifier for the repository
        chunks: List of dicts with 'id', 'document', 'embedding', 'metadata'

    Returns:
        Number of chunks stored
    """
    collection = get_or_create_collection(repo_id)

    # ChromaDB expects parallel lists
    ids = [chunk["id"] for chunk in chunks]
    documents = [chunk["document"] for chunk in chunks]
    embeddings = [chunk["embedding"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]

    # Upsert in batches (ChromaDB handles deduplication by ID)
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        collection.upsert(
            ids=ids[i : i + batch_size],
            documents=documents[i : i + batch_size],
            embeddings=embeddings[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )

    return len(ids)


def query_similar(repo_id: str, query: str, n_results: int = 8) -> list[dict]:
    """
    Find the most similar code chunks to a query.

    Args:
        repo_id: Repository identifier
        query: Natural language question
        n_results: Number of results to return

    Returns:
        List of dicts with 'document', 'metadata', 'distance'
    """
    collection = get_or_create_collection(repo_id)

    # Generate query embedding (uses retrieval_query task type)
    query_embedding = generate_query_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    # Flatten results from ChromaDB's nested format
    similar_chunks = []
    if results["documents"] and results["documents"][0]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            similar_chunks.append({
                "document": doc,
                "metadata": meta,
                "distance": dist,
                "relevance_score": 1 - dist,  # Convert distance to similarity
            })

    return similar_chunks


def delete_collection(repo_id: str) -> None:
    """Delete a repository's collection from ChromaDB."""
    client = get_chroma_client()
    try:
        client.delete_collection(f"repo_{repo_id}")
    except ValueError:
        pass  # Collection doesn't exist


def list_collections() -> list[str]:
    """List all indexed repository IDs."""
    client = get_chroma_client()
    collections = client.list_collections()
    return [col.name.replace("repo_", "") for col in collections]
