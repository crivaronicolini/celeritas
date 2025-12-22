from datetime import datetime

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage
from sqlmodel import col, select

from app.core.agent import OutputSchema, agent
from app.db import SessionDep
from app.models import (
    Document,
    Feedback,
    FeedbackRequest,
    Interaction,
    MessageRequest,
    MessageResponse,
)

router = APIRouter(tags=["chat"])


@router.post("/message", response_model=MessageResponse)
async def message(msg: MessageRequest, db: SessionDep):
    """
    Accepts a natural language question and returns an answer based on documents
    retrieved by the agent. Tracks which documents were actually used.
    """

    start_time = datetime.now()

    # Invoke the agent with the question
    try:
        agent_response: OutputSchema = (
            await agent.ainvoke({"messages": [HumanMessage(content=msg.question)]})
        )["structured_response"]
        # TODO: better handling of errors
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Agent failed to process query: {e}"
        )

    end_time = datetime.now()
    response_time = (end_time - start_time).total_seconds()

    # Track which documents were used based on agent's response
    used_documents = db.exec(
        select(Document).where(
            col(Document.filename).in_(agent_response.used_documents)
        )
    ).all()

    interaction = Interaction(
        question=msg.question,
        answer=agent_response.answer,
        response_time=response_time,
        documents=used_documents,
        timestamp=None,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    return MessageResponse(
        answer=agent_response.answer,
        interaction_id=interaction.id,
        source_documents=used_documents,
    )


@router.post("/feedback")
async def submit_feedback(feedback_req: FeedbackRequest, db: SessionDep):
    """
    Submits user feedback (thumbs up/down) for a specific interaction.
    """
    interaction = db.get(Interaction, feedback_req.interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found.")

    existing_feedback = interaction.feedback

    if existing_feedback:
        # Update existing feedback
        existing_feedback.is_positive = feedback_req.is_positive
        db.add(existing_feedback)
        db.commit()
        db.refresh(existing_feedback)
        return {"message": "Feedback updated successfully."}
    else:
        # Create new feedback
        new_feedback = Feedback(
            interaction_id=feedback_req.interaction_id,
            is_positive=feedback_req.is_positive,
        )
        db.add(new_feedback)
        db.commit()
        db.refresh(new_feedback)
        return {"message": "Feedback submitted successfully."}
