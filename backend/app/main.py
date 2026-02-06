"""
TASKIO PRO - Enterprise AI Ticket Classification
FastAPI + LangChain + ChromaDB + PostgreSQL
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import tickets, analytics, health
from app.core.database import init_db, close_db
from app.core.vector_store import init_vector_store
from app.core.cache import init_cache, close_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle"""
    print("🚀 Starting Taskio Pro Backend...")
    
    await init_db()
    print("✅ PostgreSQL connected")
    
    await init_cache()
    print("✅ Redis connected")
    
    await init_vector_store()
    print("✅ ChromaDB vector store ready")
    
    print("✅ LangChain agent initialized")
    print("🎯 Taskio Pro Backend ready!")
    
    yield
    
    await close_db()
    await close_cache()
    print("👋 Shutdown complete")


app = FastAPI(
    title="Taskio Pro API",
    description="Enterprise AI Ticket Classification with RAG",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(tickets.router, prefix="/api/tickets", tags=["Tickets"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])


@app.get("/")
async def root():
    return {
        "name": "Taskio Pro API",
        "version": "2.0.0",
        "stack": {
            "backend": "FastAPI + Python 3.11",
            "ai": "LangChain + Gemini 1.5",
            "vector_db": "ChromaDB",
            "database": "PostgreSQL",
            "cache": "Redis"
        }
    }
