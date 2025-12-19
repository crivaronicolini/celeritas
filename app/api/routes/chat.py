from datetime import datetime

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage
from sqlmodel import select

from app.core.agent import OutputSchema, agent
from app.db import SessionDep
from app.models import (
    Document,
    Feedback,
    FeedbackRequest,
    Interaction,
    InteractionDocument,
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

    # Create the interaction record
    interaction = Interaction(
        question=msg.question,
        answer=agent_response.answer,
        response_time=response_time,
    )
    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    # Track which documents were used based on agent's response
    used_document_filenames = []
    if agent_response.used_documents:
        for idx, doc_filename in enumerate(agent_response.used_documents, start=1):
            # Find the document in the database by filename
            statement = select(Document).where(Document.filename == doc_filename)
            document = db.exec(statement).first()

            if document:
                interaction_doc = InteractionDocument(
                    interaction_id=interaction.id,
                    document_id=document.id,
                    usage_order=idx,  # Track the order in which documents were used
                )
                db.add(interaction_doc)
                used_document_filenames.append(doc_filename)
            else:
                # Log warning if agent references a document that doesn't exist in DB
                print(
                    f"Warning: Agent referenced document '{doc_filename}' which is not in the database"
                )

        db.commit()

    return MessageResponse(
        answer=agent_response.answer,
        interaction_id=interaction.id,
        source_documents=used_document_filenames,
    )


@router.post("/feedback")
async def submit_feedback(feedback_req: FeedbackRequest, db: SessionDep):
    """
    Submits user feedback (thumbs up/down) for a specific interaction.
    """
    interaction = db.get(Interaction, feedback_req.interaction_id)
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found.")

    # Check if feedback already exists for this interaction
    existing_feedback = db.exec(
        select(Feedback).where(Feedback.interaction_id == feedback_req.interaction_id)
    ).first()

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
