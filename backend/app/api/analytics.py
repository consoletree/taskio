"""
Analytics API Routes
Dashboard metrics and insights
"""

from fastapi import APIRouter

from app.models.schemas import AnalyticsOverview, AccuracyStats, CategoryStat
from app.core.database import get_analytics
from app.core.cache import get_cache_stats
from app.core.vector_store import get_vector_store_stats

router = APIRouter()


@router.get("/overview", response_model=AnalyticsOverview)
async def get_overview():
    """
    Get comprehensive analytics overview
    
    Includes:
    - Total tickets processed
    - Classification accuracy (based on human corrections)
    - Category distribution
    - Cache performance
    - Vector store stats
    """
    
    # Database stats
    db_stats = await get_analytics()
    
    # Cache stats
    cache_stats = await get_cache_stats()
    
    # Vector store stats
    vector_stats = await get_vector_store_stats()
    
    total = db_stats["total_tickets"] or 1
    reviewed = db_stats["reviewed"] or 0
    correct = db_stats["correct"] or 0
    
    accuracy_pct = (correct / reviewed * 100) if reviewed > 0 else 0
    
    # Build category distribution
    categories = []
    for cat in db_stats.get("categories", []):
        categories.append(CategoryStat(
            category=cat["category"],
            count=cat["count"],
            percentage=round(cat["count"] / total * 100, 1)
        ))
    
    return AnalyticsOverview(
        total_tickets=db_stats["total_tickets"],
        accuracy=AccuracyStats(
            total_reviewed=reviewed,
            correct_predictions=correct,
            accuracy_percentage=round(accuracy_pct, 1)
        ),
        category_distribution=categories,
        avg_confidence=round((db_stats.get("avg_confidence") or 0) * 100, 1),
        cache_hit_rate=cache_stats.get("hit_rate", 0),
        vector_store_count=vector_stats.get("count", 0)
    )


@router.get("/cache")
async def get_cache_analytics():
    """Get detailed cache performance metrics"""
    return await get_cache_stats()


@router.get("/vector-store")
async def get_vector_analytics():
    """Get vector store statistics including category distribution"""
    return await get_vector_store_stats()


@router.get("/accuracy-trend")
async def get_accuracy_trend():
    """
    Get accuracy trend over time
    (Would require time-series data in production)
    """
    # Placeholder - would aggregate by day/week in production
    return {
        "trend": "stable",
        "current": 87.5,
        "previous_week": 85.2,
        "change": 2.3
    }
