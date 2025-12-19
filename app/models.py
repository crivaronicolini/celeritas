from datetime import datetime
from typing import List, Optional, Dict

from fastapi import UploadFile
from sqlmodel import TIMESTAMP, Column, Field, Relationship, SQLModel, text


# Document Models
class DocumentBase(SQLModel):
    filename: str = Field(unique=True, index=True)


class Document(DocumentBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    uploaded_at: datetime | None = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    # Relationship through junction table
    interaction_links: List["InteractionDocument"] = Relationship(
        back_populates="document"
    )


class DocumentPublic(DocumentBase):
    id: int
    uploaded_at: datetime


# Feedback Models
class FeedbackBase(SQLModel):
    is_positive: bool


class Feedback(FeedbackBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    interaction_id: int | None = Field(default=None, foreign_key="interaction.id")
    interaction: Optional["Interaction"] = Relationship(back_populates="feedback")


class FeedbackCreate(FeedbackBase):
    interaction_id: int


class FeedbackPublic(FeedbackBase):
    id: int
    interaction_id: int


class FeedbackRequest(SQLModel):
    interaction_id: int
    is_positive: bool


# Interaction Models
class InteractionBase(SQLModel):
    question: str = Field(index=True)
    answer: str


class Interaction(InteractionBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime | None = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
        )
    )
    response_time: float

    # Relationships
    document_links: List["InteractionDocument"] = Relationship(
        back_populates="interaction"
    )
    feedback: Optional["Feedback"] = Relationship(back_populates="interaction")


class InteractionCreate(InteractionBase):
    """Model for creating interactions with document references"""

    response_time: float
    document_filenames: List[str] = Field(default_factory=list)


class InteractionPublic(InteractionBase):
    """Public model that includes used documents"""

    id: int
    timestamp: datetime
    response_time: float
    used_documents: List[str] = Field(default_factory=list)


class InteractionDocument(SQLModel, table=True):
    """
    Junction table to track which documents were used in each interaction.
    This allows multiple documents to be associated with a single interaction.
    """

    interaction_id: int = Field(foreign_key="interaction.id", primary_key=True)
    document_id: int = Field(foreign_key="document.id", primary_key=True)

    # Track the relevance or order in which documents were used
    relevance_score: float | None = None
    usage_order: int | None = None

    # Relationships
    interaction: Interaction = Relationship(back_populates="document_links")
    document: Document = Relationship(back_populates="interaction_links")


# API Specific Models (not directly tied to a table)
class MessageRequest(SQLModel):
    question: str


class MessageResponse(SQLModel):
    answer: str
    interaction_id: int
    source_documents: List[str] = Field(default_factory=list)


class UploadResponse(SQLModel):
    successful_uploads: List[DocumentPublic]
    failed_uploads: List[Dict[str, str]]
