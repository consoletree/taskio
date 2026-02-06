"""
PostgreSQL Database Service with SQLAlchemy Async
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Float, Text, DateTime, select, func, text
from sqlalchemy.dialects.postgresql import UUID
import uuid

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://taskio:taskio_secret@localhost:5432/taskio_db")

engine = None
async_session: Optional[async_sessionmaker] = None


class Base(DeclarativeBase):
    pass


class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    predicted_category = Column(String(50))
    actual_category = Column(String(50))
    confidence_score = Column(Float)
    reasoning = Column(Text)
    status = Column(String(20), default="open")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FeedbackLog(Base):
    __tablename__ = "feedback_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), nullable=False)
    old_label = Column(String(50))
    new_label = Column(String(50))
    feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


async def init_db():
    """Initialize database connection"""
    global engine, async_session
    engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def close_db():
    """Close database connection"""
    global engine
    if engine:
        await engine.dispose()


def get_session() -> AsyncSession:
    """Get database session"""
    if not async_session:
        raise RuntimeError("Database not initialized")
    return async_session()


async def create_ticket(
    title: str,
    description: str,
    predicted_category: Optional[str] = None,
    confidence_score: Optional[float] = None,
    reasoning: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new ticket"""
    async with get_session() as session:
        ticket = Ticket(
            title=title,
            description=description,
            predicted_category=predicted_category,
            confidence_score=confidence_score,
            reasoning=reasoning,
            status="classified" if predicted_category else "open"
        )
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        
        return {
            "id": str(ticket.id),
            "title": ticket.title,
            "description": ticket.description,
            "predicted_category": ticket.predicted_category,
            "actual_category": ticket.actual_category,
            "confidence_score": ticket.confidence_score,
            "reasoning": ticket.reasoning,
            "status": ticket.status,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at
        }


async def get_ticket(ticket_id: str) -> Optional[Dict[str, Any]]:
    """Get ticket by ID"""
    async with get_session() as session:
        result = await session.execute(
            select(Ticket).where(Ticket.id == uuid.UUID(ticket_id))
        )
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            return None
            
        return {
            "id": str(ticket.id),
            "title": ticket.title,
            "description": ticket.description,
            "predicted_category": ticket.predicted_category,
            "actual_category": ticket.actual_category,
            "confidence_score": ticket.confidence_score,
            "reasoning": ticket.reasoning,
            "status": ticket.status,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at
        }


async def get_tickets(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    category: Optional[str] = None
) -> tuple[List[Dict[str, Any]], int]:
    """Get paginated tickets"""
    async with get_session() as session:
        query = select(Ticket)
        count_query = select(func.count(Ticket.id))
        
        if status:
            query = query.where(Ticket.status == status)
            count_query = count_query.where(Ticket.status == status)
        
        if category:
            query = query.where(Ticket.predicted_category == category)
            count_query = count_query.where(Ticket.predicted_category == category)
        
        # Get total
        total_result = await session.execute(count_query)
        total = total_result.scalar()
        
        # Get tickets
        query = query.order_by(Ticket.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await session.execute(query)
        tickets = result.scalars().all()
        
        return [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "predicted_category": t.predicted_category,
                "actual_category": t.actual_category,
                "confidence_score": t.confidence_score,
                "reasoning": t.reasoning,
                "status": t.status,
                "created_at": t.created_at,
                "updated_at": t.updated_at
            }
            for t in tickets
        ], total


async def update_ticket_correction(
    ticket_id: str,
    corrected_category: str,
    feedback: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Update ticket with human correction"""
    async with get_session() as session:
        result = await session.execute(
            select(Ticket).where(Ticket.id == uuid.UUID(ticket_id))
        )
        ticket = result.scalar_one_or_none()
        
        if not ticket:
            return None
        
        old_label = ticket.predicted_category
        ticket.actual_category = corrected_category
        ticket.status = "corrected"
        ticket.updated_at = datetime.utcnow()
        
        # Log feedback
        log = FeedbackLog(
            ticket_id=ticket.id,
            old_label=old_label,
            new_label=corrected_category,
            feedback=feedback
        )
        session.add(log)
        
        await session.commit()
        await session.refresh(ticket)
        
        return {
            "id": str(ticket.id),
            "title": ticket.title,
            "description": ticket.description,
            "predicted_category": ticket.predicted_category,
            "actual_category": ticket.actual_category,
            "confidence_score": ticket.confidence_score,
            "reasoning": ticket.reasoning,
            "status": ticket.status,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at
        }


async def get_analytics() -> Dict[str, Any]:
    """Get analytics data"""
    async with get_session() as session:
        # Total tickets
        total = await session.execute(select(func.count(Ticket.id)))
        total_count = total.scalar()
        
        # Accuracy stats
        reviewed = await session.execute(
            select(func.count(Ticket.id)).where(Ticket.actual_category.isnot(None))
        )
        reviewed_count = reviewed.scalar()
        
        correct = await session.execute(
            select(func.count(Ticket.id)).where(Ticket.predicted_category == Ticket.actual_category)
        )
        correct_count = correct.scalar()
        
        # Category distribution
        categories = await session.execute(
            select(Ticket.predicted_category, func.count(Ticket.id))
            .where(Ticket.predicted_category.isnot(None))
            .group_by(Ticket.predicted_category)
        )
        
        # Avg confidence
        avg_conf = await session.execute(
            select(func.avg(Ticket.confidence_score))
            .where(Ticket.confidence_score.isnot(None))
        )
        
        return {
            "total_tickets": total_count,
            "reviewed": reviewed_count,
            "correct": correct_count,
            "categories": [{"category": c, "count": n} for c, n in categories.all()],
            "avg_confidence": avg_conf.scalar() or 0
        }


async def check_connection() -> bool:
    """Check database connection"""
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
            return True
    except:
        return False
