"""
Health Check API Routes
Service status monitoring
"""

from fastapi import APIRouter

from app.models.schemas import HealthResponse, ServiceHealth
from app.core.database import check_connection as check_db
from app.core.cache import check_connection as check_cache
from app.core.vector_store import get_vector_store_stats
from app.services.classifier import get_agent_health

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive health check for all services
    
    Checks:
    - PostgreSQL database
    - Redis cache
    - ChromaDB vector store
    - LangChain/Gemini agent
    """
    
    services = []
    all_healthy = True
    
    # PostgreSQL
    pg_ok = await check_db()
    services.append(ServiceHealth(
        name="PostgreSQL",
        status="healthy" if pg_ok else "unhealthy"
    ))
    all_healthy = all_healthy and pg_ok
    
    # Redis
    redis_ok = await check_cache()
    services.append(ServiceHealth(
        name="Redis",
        status="healthy" if redis_ok else "unhealthy"
    ))
    all_healthy = all_healthy and redis_ok
    
    # ChromaDB
    vector_stats = await get_vector_store_stats()
    chroma_ok = vector_stats.get("connected", False)
    services.append(ServiceHealth(
        name="ChromaDB",
        status="healthy" if chroma_ok else "unhealthy",
        details={"documents": vector_stats.get("count", 0)}
    ))
    all_healthy = all_healthy and chroma_ok
    
    # LangChain Agent
    agent_health = await get_agent_health()
    agent_ok = agent_health.get("status") == "healthy"
    services.append(ServiceHealth(
        name="LangChain Agent",
        status="healthy" if agent_ok else "unhealthy",
        details={"model": agent_health.get("model", "unknown")}
    ))
    all_healthy = all_healthy and agent_ok
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        services=services,
        version="2.0.0"
    )


@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe"""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness():
    """Kubernetes readiness probe"""
    pg_ok = await check_db()
    return {
        "status": "ready" if pg_ok else "not_ready",
        "database": pg_ok
    }
