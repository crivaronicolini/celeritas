import asyncio
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, UploadFile
from sqlmodel import select

from app.core.config import settings
from app.core.document import vector_store
from app.db import SessionDep
from app.models import Document, DocumentPublic, UploadResponse

router = APIRouter(tags=["documents"])


@router.delete("/", response_model=list[DocumentPublic])
def delete_all_docs(db: SessionDep):
    all_docs = db.exec(select(Document)).all()
    for doc in all_docs:
        db.delete(doc)
    db.commit()
    vector_store.delete_all_docs()
    return all_docs


@router.get("/")
def list_documents(db: SessionDep):
    return db.exec(select(Document)).all()


@router.post("/", response_model=UploadResponse)
async def upload_documents(db: SessionDep, files: List[UploadFile] = File(...)):
    """
    Upload one or more PDF documents for processing and storage.
    """
    # Makes a first pass over the documents to discard repeated/invalid ones
    # Then makes an async group to process the embeddings for all files

    successful_uploads = []
    failed_uploads = []

    valid_files_to_process = []
    for file in files:
        if file.content_type != "application/pdf":
            failed_uploads.append(
                {"filename": file.filename, "error": "Only PDF files are allowed."}
            )
            continue

        upload_dir = Path(settings.DOC_DIR_PATH)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / Path(file.filename)

        # Check for duplicates
        # this query is ok for SQLite, we should query every
        # filename at once if we use a network DB
        db_document = db.exec(
            select(Document).where(Document.filename == file.filename)
        ).first()
        if db_document:
            failed_uploads.append(
                {
                    "filename": file.filename,
                    "error": "Document with this filename already exists.",
                }
            )
            continue

        # Save the file
        try:
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        finally:
            file.file.close()

        db_document = Document(filename=file.filename)
        db.add(db_document)
        valid_files_to_process.append((db_document, file_path))

    if not valid_files_to_process:
        return UploadResponse(successful_uploads=[], failed_uploads=failed_uploads)

    db.commit()
    for doc, _ in valid_files_to_process:
        db.refresh(doc)

    # --- Asynchronous Embedding Calculation ---
    processing_tasks = []
    for db_document, file_path in valid_files_to_process:
        processing_tasks.append(vector_store.process_pdf(file_path))

    results = await asyncio.gather(*processing_tasks, return_exceptions=True)

    # --- Cleanup and Response ---
    for i, result in enumerate(results):
        db_document, _ = valid_files_to_process[i]
        if isinstance(result, Exception):
            failed_uploads.append(
                {
                    "filename": db_document.filename,
                    "error": f"Failed to process PDF: {result}",
                }
            )
            # Roll back the DB entry for the failed document
            db.delete(db_document)
        else:
            # Need to create the DocumentPublic object manually.
            successful_uploads.append(
                DocumentPublic(
                    id=db_document.id,
                    filename=db_document.filename,
                    uploaded_at=db_document.uploaded_at,
                )
            )

    db.commit()

    return UploadResponse(
        successful_uploads=successful_uploads, failed_uploads=failed_uploads
    )
