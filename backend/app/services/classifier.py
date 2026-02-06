"""
LangChain Classification Agent with RAG
Demonstrates enterprise AI patterns: Chain composition, RAG, structured output
"""

import os
import time
from typing import Optional, Dict, Any, List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field

from app.core.vector_store import find_similar_tickets
from app.core.cache import get_cached, set_cached, make_cache_key


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

CATEGORIES = [
    "Product Issue",
    "Software Issue",
    "Network Issue", 
    "Battery Issue",
    "General Question"
]

CATEGORY_DEFINITIONS = """
- **Product Issue**: Physical hardware problems - cracked screens, broken buttons, damaged devices, defective parts, manufacturing issues
- **Software Issue**: Application problems - crashes, bugs, errors, failed installations, update issues, freezing, performance problems
- **Network Issue**: Connectivity problems - WiFi not working, internet outages, VPN failures, slow connections, Bluetooth issues
- **Battery Issue**: Power problems - fast draining, won't charge, overheating while charging, battery percentage issues, power-off problems  
- **General Question**: Information requests - how-to questions, account help, password resets, feature inquiries, general support
"""


class ClassificationResult(BaseModel):
    """Structured output schema for classification"""
    category: str = Field(description="One of: Product Issue, Software Issue, Network Issue, Battery Issue, General Question")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")
    reasoning: str = Field(description="2-3 sentence explanation for the classification")
    key_indicators: List[str] = Field(description="List of 2-4 key phrases that influenced the decision")


def get_llm() -> ChatGoogleGenerativeAI:
    """Initialize Gemini LLM via LangChain"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
        convert_system_message_to_human=True
    )


def build_classification_chain():
    """
    Build LangChain classification chain with RAG context
    Demonstrates: Prompt engineering, chain composition, structured output
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ("human", """You are an expert support ticket classifier for a technology company.

## Your Task
Classify the support ticket below into exactly ONE category.

## Categories
{categories}

## Similar Past Tickets (for context)
{similar_tickets}

## Ticket to Classify
**Title:** {title}
**Description:** {description}

## Instructions
1. Analyze the ticket content carefully
2. Consider the similar past tickets for context
3. Choose the single most appropriate category
4. Provide confidence based on clarity (0.9+ for obvious, 0.7-0.9 for clear, 0.5-0.7 for ambiguous)

## Required Output Format (JSON only, no markdown)
{{"category": "<category name>", "confidence": <0.0-1.0>, "reasoning": "<explanation>", "key_indicators": ["<phrase1>", "<phrase2>"]}}""")
    ])
    
    llm = get_llm()
    parser = JsonOutputParser(pydantic_object=ClassificationResult)
    
    chain = prompt | llm | parser
    
    return chain


async def classify_ticket(
    title: Optional[str],
    description: str,
    use_cache: bool = True,
    use_rag: bool = True
) -> Dict[str, Any]:
    """
    Main classification function using LangChain with RAG
    
    Args:
        title: Optional ticket title
        description: Ticket description
        use_cache: Whether to check/store in Redis cache
        use_rag: Whether to use similar tickets for context
    
    Returns:
        Classification result with metadata
    """
    start_time = time.time()
    full_text = f"{title}. {description}" if title else description
    
    # Check cache first
    if use_cache:
        cache_key = make_cache_key(full_text)
        cached = await get_cached(cache_key)
        if cached:
            return {
                **cached,
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "cached": True,
                "rag_used": False
            }
    
    # Get similar tickets for RAG context
    similar_context = "No similar tickets found."
    similar_tickets = []
    
    if use_rag:
        similar = await find_similar_tickets(full_text, n_results=3)
        if similar:
            similar_tickets = similar
            similar_context = "\n".join([
                f"- [{s['category']}] \"{s['text'][:80]}...\" (similarity: {s['similarity']:.0%})"
                for s in similar
            ])
    
    # Build and run chain
    chain = build_classification_chain()
    
    try:
        result = await chain.ainvoke({
            "categories": CATEGORY_DEFINITIONS,
            "similar_tickets": similar_context,
            "title": title or "No title provided",
            "description": description
        })
        
        # Validate category
        if result.get("category") not in CATEGORIES:
            for cat in CATEGORIES:
                if cat.lower() in str(result.get("category", "")).lower():
                    result["category"] = cat
                    break
            else:
                result["category"] = "General Question"
        
        # Normalize confidence
        result["confidence"] = min(max(float(result.get("confidence", 0.5)), 0), 1)
        
        # Add metadata
        result["similar_tickets"] = [
            {"id": s["id"], "category": s["category"], "similarity": round(s["similarity"], 2)}
            for s in similar_tickets
        ]
        
        # Cache result
        if use_cache:
            await set_cached(cache_key, result)
        
        latency = round((time.time() - start_time) * 1000, 2)
        
        return {
            **result,
            "latency_ms": latency,
            "cached": False,
            "rag_used": bool(similar_tickets)
        }
        
    except Exception as e:
        print(f"LangChain error: {e}")
        # Fallback to keyword classification
        result = keyword_fallback(full_text)
        result["latency_ms"] = round((time.time() - start_time) * 1000, 2)
        result["cached"] = False
        result["rag_used"] = False
        result["fallback"] = True
        return result


def keyword_fallback(text: str) -> Dict[str, Any]:
    """Keyword-based fallback when LLM fails"""
    text_lower = text.lower()
    
    patterns = {
        "Product Issue": ["broken", "cracked", "damaged", "defective", "screen", "hardware", "physical", "button"],
        "Software Issue": ["crash", "bug", "error", "install", "update", "app", "software", "freeze", "slow"],
        "Network Issue": ["wifi", "internet", "connection", "network", "vpn", "connect", "online", "bluetooth"],
        "Battery Issue": ["battery", "charging", "charge", "drain", "power", "dies", "percentage"],
        "General Question": ["how to", "how do", "what is", "password", "account", "help", "reset", "where"]
    }
    
    scores = {cat: sum(1 for kw in kws if kw in text_lower) for cat, kws in patterns.items()}
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = min(0.4 + (scores[best] / max(total, 1)) * 0.4, 0.7) if total > 0 else 0.3
    
    return {
        "category": best,
        "confidence": round(confidence, 2),
        "reasoning": "Classified using keyword matching (fallback mode)",
        "key_indicators": [kw for kw in patterns[best] if kw in text_lower][:3],
        "similar_tickets": []
    }


async def get_agent_health() -> Dict[str, Any]:
    """Check agent configuration status"""
    try:
        llm = get_llm()
        return {
            "status": "healthy",
            "model": "gemini-1.5-flash",
            "provider": "Google AI",
            "categories": CATEGORIES
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
