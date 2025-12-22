from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import selectinload, with_parent
from sqlmodel import func, select, col
from app.db import SessionDep
from app.models import Document, Interaction, Feedback
from typing import List, Dict, Any

router = APIRouter(tags=["analytics"])


@router.get("/")
async def get_analytics(db: SessionDep) -> Dict[str, Any]:
    """
    Provides comprehensive analytics on document usage and common questions.
    Now properly tracks multiple documents per interaction.
    """
    analytics_data = {}

    # 1. Which documents are queried most frequently?
    document_query_counts = db.exec(
        select(
            Document.filename,
            query_count := func.count(Interaction.id),
        )
        .select_from(Document)
        .join(Document.interactions)
        .group_by(Document.filename)
        .order_by(query_count.desc())
    ).all()

    analytics_data["most_frequently_queried_documents"] = [
        {"filename": doc_name, "query_count": count}
        for doc_name, count in document_query_counts
    ]

    # 2. What questions are asked most often?
    question_counts = db.exec(
        select(Interaction.question, ask_count := func.count(Interaction.id))
        .group_by(Interaction.question)
        .order_by(ask_count.desc())
        .limit(20)
    ).all()

    analytics_data["most_often_asked_questions"] = [
        {"question": q_text, "ask_count": count} for q_text, count in question_counts
    ]

    # 3. How many queries were answered from each PDF this week?
    seven_days_ago = datetime.now() - timedelta(days=7)
    weekly_query_counts = db.exec(
        select(
            Document.filename,
            weekly_query_count := func.count(Interaction.id),
        )
        .select_from(Document)
        .join(Document.interactions)
        .where(Interaction.timestamp >= seven_days_ago)
        .group_by(Document.filename)
        .order_by(weekly_query_count.desc())
    ).all()

    analytics_data["weekly_queries_per_document"] = [
        {"filename": doc_name, "weekly_query_count": count}
        for doc_name, count in weekly_query_counts
    ]

    # 4. Average response time
    avg_response_time = db.exec(
        select(func.avg(Interaction.response_time))
    ).one_or_none()

    analytics_data["average_response_time_seconds"] = (
        round(avg_response_time, 3) if avg_response_time else 0
    )

    # 5. Feedback statistics
    feedbacks = db.exec(
        select(
            func.count(col(Feedback.id)).label("total_feedback"),
            func.count(col(Feedback.id))
            .filter(col(Feedback.is_positive))
            .label("positive_feedback"),
        )
    ).one()
    total_feedback = feedbacks.total_feedback
    positive_feedback = feedbacks.positive_feedback

    analytics_data["feedback_statistics"] = {
        "total_feedback_count": total_feedback,
        "positive_feedback_count": positive_feedback,
        "negative_feedback_count": total_feedback - positive_feedback,
        "positive_feedback_percentage": (
            round((positive_feedback / total_feedback) * 100, 2)
            if total_feedback > 0
            else 0
        ),
    }

    # 6. Total interactions count
    total_interactions = db.exec(select(func.count(Interaction.id))).one() or 0
    analytics_data["total_interactions"] = total_interactions

    return analytics_data


@router.get("/document/{document_id}")
async def get_document_analytics(document_id: int, db: SessionDep) -> Dict[str, Any]:
    """
    Get detailed analytics for a specific document.
    """
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Get recent questions that used this document
    doc_interactions = document.interactions

    # Get all interactions that used this document
    interactions_count = len(doc_interactions)

    recent_questions = [
        {
            "question": interaction.question,
            "timestamp": interaction.timestamp,
            "response_time": interaction.response_time,
        }
        for interaction in doc_interactions
    ]

    # Average response time for queries using this document
    avg_response_time = db.exec(
        select(func.avg(Interaction.response_time))
        .select_from(Interaction)
        .where(with_parent(document, Document.interactions))
    ).one_or_none()

    return {
        "document_id": document.id,
        "filename": document.filename,
        "uploaded_at": document.uploaded_at,
        "total_uses": interactions_count,
        "recent_questions": recent_questions,
        "average_response_time_seconds": (
            round(avg_response_time, 3) if avg_response_time else 0
        ),
    }


@router.get("/interactions/recent")
async def get_recent_interactions(
    db: SessionDep, limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get the most recent interactions with their associated documents.
    """
    interactions = db.exec(
        select(Interaction)
        .options(selectinload(Interaction.documents))
        .order_by(col(Interaction.timestamp).desc())
        .limit(limit)
    ).all()

    result = []
    for interaction in interactions:
        documents = interaction.documents

        result.append(
            {
                "id": interaction.id,
                "question": interaction.question,
                "answer": interaction.answer[:200] + "..."
                if len(interaction.answer) > 200
                else interaction.answer,
                "timestamp": interaction.timestamp,
                "response_time": interaction.response_time,
                "used_documents": [doc.filename for doc in documents],
            }
        )

    return result


@router.get("/documents/unused")
async def get_unused_documents(db: SessionDep) -> List[Dict[str, Any]]:
    """
    Find documents that have been uploaded but never used in any interaction.
    """

    # Get all documents that don't have any entries in InteractionDocument
    unused_documents = db.exec(
        select(Document).where(~col(Document.interactions).any())
    ).all()

    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "uploaded_at": doc.uploaded_at,
        }
        for doc in unused_documents
    ]


@router.get("/questions/unanswered-patterns")
async def get_unanswered_patterns(db: SessionDep) -> Dict[str, Any]:
    """
    Identify patterns in questions that might not have good answers.
    This looks at interactions with no documents used or negative feedback.
    """
    # Questions where no documents were used (agent couldn't find relevant info)
    questions_without_docs = db.exec(
        select(Interaction)
        .where(~col(Interaction.documents).any())
        .order_by(col(Interaction.timestamp).desc())
        .limit(20)
    ).all()

    # Questions with negative feedback
    questions_with_negative_feedback = db.exec(
        select(Interaction)
        .join(Feedback)
        .where(~col(Feedback.is_positive))
        .order_by(col(Interaction.timestamp).desc())
        .limit(20)
    ).all()

    return {
        "questions_without_documents": [
            {
                "id": q.id,
                "question": q.question,
                "answer": q.answer[:200] + "..." if len(q.answer) > 200 else q.answer,
                "timestamp": q.timestamp,
            }
            for q in questions_without_docs
        ],
        "questions_with_negative_feedback": [
            {
                "id": q.id,
                "question": q.question,
                "answer": q.answer[:200] + "..." if len(q.answer) > 200 else q.answer,
                "timestamp": q.timestamp,
            }
            for q in questions_with_negative_feedback
        ],
    }
