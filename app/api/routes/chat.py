from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.agent import AgentDep
from app.core.auth import CurrentUser
from app.db import SessionDep
from app.models import (
    Conversation,
    Document,
    Feedback,
    FeedbackRequest,
    Interaction,
    MessageRequest,
    MessageResponse,
)

router = APIRouter()


@router.post("/message/{conversation_id}", response_model=MessageResponse)
async def message(
    conversation_id: str,
    msg: MessageRequest,
    db: SessionDep,
    agent: AgentDep,
    user: CurrentUser,
):
    """
    Accepts a natural language question and returns an answer based on documents
    retrieved by the agent. Tracks which documents were actually used.
    """
    conversation = await db.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    start_time = datetime.now()

    try:
        agent_response = await agent.ainvoke(msg.question, thread_id=conversation_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Agent failed to process query: {e}"
        )

    end_time = datetime.now()
    response_time = (end_time - start_time).total_seconds()

    conversation.updated_at = datetime.utcnow()
    db.add(conversation)

    result = await db.execute(
        select(Document).where(Document.filename.in_(agent_response.used_documents))
    )
    used_documents = result.scalars().all()

    interaction = Interaction(
        question=msg.question,
        answer=agent_response.answer,
        response_time=response_time,
        documents=list(used_documents),
        timestamp=None,
    )
    db.add(interaction)
    await db.commit()
    await db.refresh(interaction)

    return MessageResponse(
        answer=agent_response.answer,
        interaction_id=interaction.id,
        source_documents=list(used_documents),
    )


@router.post("/feedback")
async def submit_feedback(
    feedback_req: FeedbackRequest,
    db: SessionDep,
    user: CurrentUser,
):
    """
    Submits user feedback (thumbs up/down) for a specific interaction.
    """
    interaction = await db.get(Interaction, feedback_req.interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found.")

    existing_feedback = interaction.feedback

    if existing_feedback:
        existing_feedback.is_positive = feedback_req.is_positive
        db.add(existing_feedback)
        await db.commit()
        await db.refresh(existing_feedback)
        return {"message": "Feedback updated successfully."}
    else:
        new_feedback = Feedback(
            interaction_id=feedback_req.interaction_id,
            is_positive=feedback_req.is_positive,
        )
        db.add(new_feedback)
        await db.commit()
        await db.refresh(new_feedback)
        return {"message": "Feedback submitted successfully."}
