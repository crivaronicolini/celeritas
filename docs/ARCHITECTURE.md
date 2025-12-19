# Architecture Document

## 1. System Architecture Overview

This project is designed as a modular, multi-layered application.
Its architecture is centered around a FastAPI web server that orchestrates document processing, question answering, and data persistence.

The core components are:
- **Web Server (FastAPI):** Exposes the REST API endpoints and handles incoming HTTP requests. It acts as the main entry point to the system.
- **Document Store (Filesystem):** A designated directory (`mnt/docs`) for storing the original uploaded PDF files.
- **Relational Database (SQLite):** A simple SQL database (`mnt/db/celeritas.db`) for storing metadata about documents and all user interaction logs. This is managed via SQLModel.
- **Vector Database (ChromaDB):** A vector store (`mnt/db/vector`) that holds the embeddings generated from the content of the PDF documents. This enables efficient similarity searches to find text chunks relevant to a user's question.
- **Q&A Engine (Core Logic):** A set of functions responsible for the main business logic, including PDF parsing, interaction with the OpenAI API, and orchestrating the response generation.

## 2. Component Breakdown

The application is structured into distinct layers and components, mapping to the `app/` directory:

- **`app/api/` (API Layer):**
    - `main.py`: Mounts all the specific API route modules.
    - `routes/`: Contains the specific endpoint logic.
        - `documents.py`: Handles file uploads (`POST /api/documents/`).
        - `chat.py`: Handles the Q&A logic (`POST /api/chat/`).
        - `analytics.py`: Provides the analytics data (`GET /api/analytics/`).

- **`app/core/` (Core Logic Functions):**
    - `document.py`: Contains the document processing functions responsible for:
        - Parsing text from PDF files (using Langchain's `pymupdf4LLM` document loader).
        - Splitting extracted text into manageable chunks.
        - Storing the original PDF in the filesystem.
        - Storing text chunks and their embeddings in ChromaDB.
        - Generating embeddings for text chunks and questions via the OpenAI API.
    - `agent.py`: Contains the agent setup and Q&A functions responsible for:
        - Taking a new question, embedding it, and querying ChromaDB to find the most relevant context chunks.
        - Constructing a precise prompt for the OpenAI completion model, including the user's question and the retrieved context.
        - Returning the final answer and source citation.
    - `config.py`: Manages configuration and environment variables (like API keys).

- **`app/` (Data/Persistence Layer):**
    - `db.py`: Manages database sessions and engine creation for SQLite.
    - `models.py`: Defines the SQLModel ORM models (`Document`, `Interaction`) that map to the tables in the SQLite database. Also defines the auxiliary data models that define the data flow in the application.

## 3. Data Flow

### 3.1. Document Indexing Flow

1.  A user sends a `POST` request to `/api/documents/` with a PDF file.
2.  The PDF is saved to the `mnt/docs` directory and records its metadata in the SQLite `documents` table.
3.  The text is extracted from the PDF.
4.  The service splits the text into chunks and sends each chunk to the OpenAI API to get a vector embedding.
5.  Each text chunk and its corresponding embedding are stored together in the ChromaDB vector store.

### 3.2. Question Answering Flow

1.  A user sends a `POST` request to `/api/chat/` with a JSON payload containing the question.
2.  The Q&A function sends the user's question to the OpenAI API to generate an embedding for the question.
3.  The Q&A function uses this question embedding to perform a similarity search in ChromaDB.
5.  ChromaDB returns the most relevant text chunks from the documents.
5.  The Q&A function constructs a detailed prompt containing the original question and the retrieved text chunks as context.
7.  This prompt is sent to the OpenAI chat API.
8.  OpenAI returns a generated answer.
9.  The Q&A function logs the full interaction (question, answer, source, timings) to the `interactions` table in SQLite.
10. The final answer and source document are returned in the API response.
