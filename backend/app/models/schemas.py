"""
Pydantic Schemas for Request/Response Validation
"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from enum import Enum


class TicketCategory(str, Enum):
    PRODUCT = "Product Issue"
    SOFTWARE = "Software Issue"
    NETWORK = "Network Issue"
    BATTERY = "Battery Issue"
    GENERAL = "General Question"


class TicketStatus(str, Enum):
    OPEN = "open"
    CLASSIFIED = "classified"
    CORRECTED = "corrected"
    RESOLVED = "resolved"


# === Request Schemas ===

class TicketCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: str = Field(..., min_length=10, max_length=5000)


class TicketCorrection(BaseModel):
    corrected_category: TicketCategory
    feedback: Optional[str] = Field(None, max_length=1000)


# === Response Schemas ===

class SimilarTicket(BaseModel):
    id: str
    category: Optional[str]
    similarity: float


class ClassificationResponse(BaseModel):
    category: str
    confidence: float = Field(..., ge=0, le=1)
    reasoning: str
    key_indicators: List[str] = []
    similar_tickets: List[SimilarTicket] = []
    latency_ms: float
    cached: bool
    rag_used: bool = False


class TicketResponse(BaseModel):
    id: str
    title: str
    description: str
    predicted_category: Optional[str]
    actual_category: Optional[str]
    confidence_score: Optional[float]
    reasoning: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime


class TicketWithClassification(BaseModel):
    ticket: TicketResponse
    classification: ClassificationResponse


class PaginatedTickets(BaseModel):
    tickets: List[TicketResponse]
    total: int
    page: int
    limit: int
    pages: int


# === Analytics Schemas ===

class CategoryStat(BaseModel):
    category: str
    count: int
    percentage: float


class AccuracyStats(BaseModel):
    total_reviewed: int
    correct_predictions: int
    accuracy_percentage: float


class AnalyticsOverview(BaseModel):
    total_tickets: int
    accuracy: AccuracyStats
    category_distribution: List[CategoryStat]
    avg_confidence: float
    cache_hit_rate: float
    vector_store_count: int


# === Health Schemas ===

class ServiceHealth(BaseModel):
    name: str
    status: str
    details: Optional[dict] = None


class HealthResponse(BaseModel):
    status: str
    services: List[ServiceHealth]
    version: str = "2.0.0"
