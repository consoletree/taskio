"""
Tickets API Routes
CRUD operations with AI classification
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    TicketCreate, TicketCorrection, TicketResponse,
    TicketWithClassification, PaginatedTickets, ClassificationResponse, SimilarTicket
)
from app.core.database import (
    create_ticket, get_ticket, get_tickets, update_ticket_correction
)
from app.core.vector_store import add_ticket_embedding
from app.services.classifier import classify_ticket, CATEGORIES

router = APIRouter()


@router.post("", response_model=TicketWithClassification, status_code=201)
async def create_and_classify(ticket: TicketCreate):
    """
    Create a new ticket and classify it using LangChain + RAG
    
    This endpoint demonstrates:
    - LangChain for LLM orchestration
    - RAG for context-aware classification
    - Vector storage for semantic search
    - Redis caching for performance
    """
    
    # Classify using LangChain agent with RAG
    result = await classify_ticket(
        title=ticket.title,
        description=ticket.description,
        use_cache=True,
        use_rag=True
    )
    
    # Persist to PostgreSQL
    title = ticket.title or ticket.description[:100]
    db_ticket = await create_ticket(
        title=title,
        description=ticket.description,
        predicted_category=result["category"],
        confidence_score=result["confidence"],
        reasoning=result.get("reasoning")
    )
    
    # Store in vector DB for future RAG queries
    await add_ticket_embedding(
        ticket_id=db_ticket["id"],
        text=f"{title}. {ticket.description}",
        category=result["category"]
    )
    
    return TicketWithClassification(
        ticket=TicketResponse(**db_ticket),
        classification=ClassificationResponse(
            category=result["category"],
            confidence=result["confidence"],
            reasoning=result.get("reasoning", ""),
            key_indicators=result.get("key_indicators", []),
            similar_tickets=[
                SimilarTicket(**s) for s in result.get("similar_tickets", [])
            ],
            latency_ms=result["latency_ms"],
            cached=result["cached"],
            rag_used=result.get("rag_used", False)
        )
    )


@router.get("", response_model=PaginatedTickets)
async def list_tickets(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None)
):
    """Get paginated list of tickets with optional filters"""
    tickets, total = await get_tickets(page, limit, status, category)
    
    return PaginatedTickets(
        tickets=[TicketResponse(**t) for t in tickets],
        total=total,
        page=page,
        limit=limit,
        pages=max(1, (total + limit - 1) // limit)
    )


@router.get("/categories")
async def get_available_categories():
    """Get list of available classification categories"""
    return {
        "categories": CATEGORIES,
        "count": len(CATEGORIES)
    }


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_single_ticket(ticket_id: str):
    """Get a single ticket by ID"""
    ticket = await get_ticket(ticket_id)
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return TicketResponse(**ticket)


@router.patch("/{ticket_id}/correct", response_model=TicketResponse)
async def correct_classification(ticket_id: str, correction: TicketCorrection):
    """
    Submit human correction for misclassified ticket
    
    This creates a feedback loop for:
    - Accuracy tracking
    - Future model improvement
    - Fine-tuning data collection
    """
    
    if correction.corrected_category.value not in CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of: {CATEGORIES}"
        )
    
    updated = await update_ticket_correction(
        ticket_id=ticket_id,
        corrected_category=correction.corrected_category.value,
        feedback=correction.feedback
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return TicketResponse(**updated)


@router.post("/classify-only", response_model=ClassificationResponse)
async def classify_without_saving(ticket: TicketCreate):
    """
    Classify a ticket without persisting (for testing/preview)
    """
    result = await classify_ticket(
        title=ticket.title,
        description=ticket.description,
        use_cache=False,  # Don't cache test classifications
        use_rag=True
    )
    
    return ClassificationResponse(
        category=result["category"],
        confidence=result["confidence"],
        reasoning=result.get("reasoning", ""),
        key_indicators=result.get("key_indicators", []),
        similar_tickets=[
            SimilarTicket(**s) for s in result.get("similar_tickets", [])
        ],
        latency_ms=result["latency_ms"],
        cached=result["cached"],
        rag_used=result.get("rag_used", False)
    )
