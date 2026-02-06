"""
ChromaDB Vector Store for RAG (Retrieval-Augmented Generation)
Stores ticket embeddings for semantic similarity search
"""

import os
from typing import Optional, List, Dict, Any
import chromadb
from chromadb.config import Settings

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8001))

client: Optional[chromadb.HttpClient] = None
collection = None


async def init_vector_store():
    """Initialize ChromaDB connection"""
    global client, collection
    
    try:
        client = chromadb.HttpClient(
            host=CHROMA_HOST,
            port=CHROMA_PORT,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create or get tickets collection
        collection = client.get_or_create_collection(
            name="tickets",
            metadata={
                "description": "Support ticket embeddings for RAG",
                "hnsw:space": "cosine"
            }
        )
        
        print(f"   └─ Collection 'tickets' has {collection.count()} documents")
        
    except Exception as e:
        print(f"⚠️ ChromaDB init failed: {e} (RAG will be disabled)")


async def add_ticket_embedding(
    ticket_id: str,
    text: str,
    category: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Add ticket to vector store for future similarity searches
    ChromaDB auto-generates embeddings using its default model
    """
    if not collection:
        return False
    
    try:
        collection.upsert(
            ids=[ticket_id],
            documents=[text],
            metadatas=[{
                "category": category,
                **(metadata or {})
            }]
        )
        return True
    except Exception as e:
        print(f"Vector store add error: {e}")
        return False


async def find_similar_tickets(
    text: str,
    n_results: int = 5,
    category_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Find semantically similar tickets using vector search
    This enables RAG - providing context to the LLM
    """
    if not collection or collection.count() == 0:
        return []
    
    try:
        where = {"category": category_filter} if category_filter else None
        
        results = collection.query(
            query_texts=[text],
            n_results=min(n_results, collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        similar = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                # Convert distance to similarity (cosine distance -> similarity)
                distance = results["distances"][0][i] if results["distances"] else 0
                similarity = 1 - distance  # For cosine, lower distance = higher similarity
                
                similar.append({
                    "id": doc_id,
                    "text": results["documents"][0][i] if results["documents"] else "",
                    "category": results["metadatas"][0][i].get("category") if results["metadatas"] else None,
                    "similarity": max(0, min(1, similarity))  # Clamp to [0, 1]
                })
        
        return similar
        
    except Exception as e:
        print(f"Vector search error: {e}")
        return []


async def get_category_examples(category: str, n: int = 3) -> List[str]:
    """Get example tickets for a category (few-shot prompting)"""
    if not collection:
        return []
    
    try:
        results = collection.get(
            where={"category": category},
            limit=n,
            include=["documents"]
        )
        return results["documents"] if results.get("documents") else []
    except:
        return []


async def delete_ticket_embedding(ticket_id: str) -> bool:
    """Remove ticket from vector store"""
    if not collection:
        return False
    
    try:
        collection.delete(ids=[ticket_id])
        return True
    except:
        return False


async def get_vector_store_stats() -> Dict[str, Any]:
    """Get vector store statistics"""
    if not collection:
        return {"connected": False, "count": 0}
    
    try:
        count = collection.count()
        
        # Get category distribution
        all_data = collection.get(include=["metadatas"])
        categories = {}
        if all_data.get("metadatas"):
            for meta in all_data["metadatas"]:
                cat = meta.get("category", "unknown")
                categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "connected": True,
            "count": count,
            "categories": categories
        }
    except Exception as e:
        return {"connected": False, "error": str(e)}
