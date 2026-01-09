from contextlib import asynccontextmanager
from typing import Annotated, Callable, List

import structlog
from fastapi import Depends, Request
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel, Field
from structlog.contextvars import bind_contextvars

from app.core.config import settings
from app.core.document import vector_store

logger = structlog.stdlib.get_logger(__name__)


class RetrieveContextArgsSchema(BaseModel):
    query: str = Field(description="The user's question or query.")


class OutputSchema(BaseModel):
    answer: str = Field(description="The answer to the user's question")
    used_documents: List[str] = Field(
        description="List of document filenames that were used to answer the question. "
        "Extract these from the 'Source:' field in the retrieved context."
    )


class AgentResponse(BaseModel):
    """Response from the agent including checkpoint reference."""

    answer: str
    used_documents: list[str]
    checkpoint_id: str


class RAGAgent:
    def __init__(
        self,
        model: BaseChatModel | Callable | None = None,
        tools: list[Callable] | None = None,
        checkpointer: AsyncSqliteSaver | None = None,
    ):
        self.sys_prompt = """You are a helpful RAG assistant.
        You can engage in casual conversation and also use your retrieval tool to augment the information you have.
        For every message from the user you must think and decide if it part of a normal conversation or if it is relevant to the users stored documents.
        If you find that is relevant to the documents, you must user your retrieval tool.

        IMPORTANT INSTRUCTIONS:
        1. Prioritize the information from the retrieved documents in your answer
        2. Pay attention to the 'Source:' field in the retrieved context - these indicate which documents you used
        3. In your response, you MUST populate the 'used_documents' field with ALL unique document filenames that appear in the 'Source:' fields of the context you retrieved
        4. Extract ONLY the filename from each Source field (e.g., if you see "Source: climate_report.pdf", add "climate_report.pdf" to used_documents)
        5. If no relevant information is found in the database, inform the user and answer to the best of your ability with your general knowledge, but leave used_documents as an empty list

        Example of correct behavior:
        - You retrieve context with "Source: document1.pdf" and "Source: document2.pdf"
        - Your response should have: used_documents = ["document1.pdf", "document2.pdf"]

        This tracking is critical for analytics and citation purposes."""

        self.model: BaseChatModel = model or ChatOpenAI(
            model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY
        )
        self.tools = tools or [self.retrieve_context]
        self.checkpointer = checkpointer
        self.agent = create_agent(
            self.model,
            self.tools,
            system_prompt=self.sys_prompt,
            response_format=OutputSchema,
            checkpointer=self.checkpointer,
        )

    @staticmethod
    @tool(args_schema=RetrieveContextArgsSchema)
    def retrieve_context(query: str) -> str:
        """Retrieve information from the vector database to help answer a query.
        Only use this tool to search information relevant to the query.
        Do not use it to engage in casual conversation.
        Args:
            query:str
                A query written by you to answer the user's query.
        Returns:
            information: str
                The found documents with their source filenames that will help answer the query.
        """
        logger.debug("retrieve_context called", query=query[:100])
        bind_contextvars(rag_query=query[:100])

        if vector_store.is_empty:
            logger.debug("vector store is empty")
            bind_contextvars(vector_store_empty=True)
            return "The document vector store is currently empty. Notify the user and suggest to upload documents."

        logger.debug("performing similarity search")
        retrieved_docs = vector_store.similarity_search(query, k=4)
        logger.debug("retrieved documents", count=len(retrieved_docs))

        sources: list[str] = []
        serialized_docs: list[str] = []
        for doc in retrieved_docs:
            source_filename: str = doc.metadata.get("source", "unknown").split("/")[-1]
            sources.append(source_filename)
            logger.debug(
                "document retrieved",
                source=source_filename,
                preview=doc.page_content[:100],
            )
            serialized_docs.append(
                f"Source: {source_filename}\nContent: {doc.page_content}"
            )

        bind_contextvars(
            documents_retrieved=len(retrieved_docs), document_sources=sources
        )
        return "\n\n".join(serialized_docs)

    async def ainvoke(self, question: str, thread_id: str) -> AgentResponse:
        logger.debug("ainvoke called", thread_id=thread_id, question=question[:100])
        config = {"configurable": {"thread_id": thread_id}}
        logger.debug("agent config", config=config)
        try:
            response = await self.agent.ainvoke(
                {"messages": [HumanMessage(content=question)]},
                config=config,
            )
            logger.debug(
                "raw agent response", keys=list(response.keys()) if response else None
            )
            structured = response["structured_response"]
            logger.debug(
                "structured_response received", answer_length=len(structured.answer)
            )

            # Get checkpoint_id from state
            state = await self.agent.aget_state(config)
            checkpoint_id = state.config["configurable"]["checkpoint_id"]
            logger.debug("checkpoint_id retrieved", checkpoint_id=checkpoint_id)

            return AgentResponse(
                answer=structured.answer,
                used_documents=structured.used_documents,
                checkpoint_id=checkpoint_id,
            )
        except KeyError as e:
            bind_contextvars(
                error_type="KeyError", error_message="Missing key in agent response"
            )
            logger.debug("missing key in agent response", error=str(e))
            raise
        except Exception as e:
            bind_contextvars(error_type=type(e).__name__, error_message=str(e))
            logger.debug("agent invocation failed", error=str(e))
            raise

    async def get_history(self, thread_id: str) -> list:
        if not self.checkpointer:
            return []
        config = {"configurable": {"thread_id": thread_id}}
        state = await self.agent.aget_state(config)
        if state and state.values:
            return state.values.get("messages", [])
        return []


@asynccontextmanager
async def lifespan_agent(app):
    """Context manager for agent lifecycle. Use in FastAPI lifespan."""
    checkpointer_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    async with AsyncSqliteSaver.from_conn_string(checkpointer_path) as checkpointer:
        app.state.agent = RAGAgent(
            model=ChatGoogleGenerativeAI(
                model="gemini-2.5-flash", api_key=settings.GEMINI_API_KEY
            ),
            checkpointer=checkpointer,
        )
        logger.debug("agent initialized", agent=repr(app.state.agent))
        yield


def get_agent(request: Request) -> RAGAgent:
    return request.app.state.agent


AgentDep = Annotated[RAGAgent, Depends(get_agent)]
