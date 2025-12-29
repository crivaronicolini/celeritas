from typing import Annotated, Callable, List

from fastapi import Depends
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.document import vector_store


class RetrieveContextArgsSchema(BaseModel):
    query: str = Field(description="The user's question or query.")


class OutputSchema(BaseModel):
    """
    Schema for agent output that includes both the answer and
    the list of documents that were used to generate the answer.
    """

    answer: str = Field(description="The answer to the user's question")
    used_documents: List[str] = Field(
        description="List of document filenames that were used to answer the question. "
        "Extract these from the 'Source:' field in the retrieved context."
    )


class RAGAgent:
    def __init__(
        self,
        model: BaseChatModel | Callable | None = None,
        tools: list[Callable] | None = None,
    ):
        self.sys_prompt = """You are a helpful RAG assistant that answers questions grounding your knowledge on the document database.

        IMPORTANT INSTRUCTIONS:
        1. Always use the retrieve_context tool to search for relevant information
        2. Prioritize the information from the retrieved documents in your answer
        3. Pay attention to the 'Source:' field in the retrieved context - these indicate which documents you used
        4. In your response, you MUST populate the 'used_documents' field with ALL unique document filenames that appear in the 'Source:' fields of the context you retrieved
        5. Extract ONLY the filename from each Source field (e.g., if you see "Source: climate_report.pdf", add "climate_report.pdf" to used_documents)
        6. If no relevant information is found in the database, inform the user and answer to the best of your ability with your general knowledge, but leave used_documents as an empty list

        Example of correct behavior:
        - You retrieve context with "Source: document1.pdf" and "Source: document2.pdf"
        - Your response should have: used_documents = ["document1.pdf", "document2.pdf"]

        This tracking is critical for analytics and citation purposes."""

        self.model: BaseChatModel = model or ChatOpenAI(
            model="gpt-5-nano", api_key=settings.OPENAI_API_KEY
        )
        self.tools = tools or [self.retrieve_context]
        self.agent = create_agent(
            self.model,
            self.tools,
            system_prompt=self.sys_prompt,
            response_format=OutputSchema,
        )

    @staticmethod
    @tool(args_schema=RetrieveContextArgsSchema)
    def retrieve_context(query: str) -> str:
        """Retrieve information from the vector database to help answer a query.
        Args:
            query:str
                A query written by you to answer the user's query.
        Returns:
            information: str
                The found documents with their source filenames that will help answer the query.
        """

        if vector_store.is_empty:
            return "The document vector store is currently empty. Notify the user and suggest to upload documents."

        retrieved_docs = vector_store.similarity_search(query, k=4)

        serialized_docs: list[str] = []
        for doc in retrieved_docs:
            # Extract just the filename from the 'source' metadata
            source_filename: str = doc.metadata.get("source", "unknown").split("/")[-1]
            serialized_docs.append(
                f"Source: {source_filename}\nContent: {doc.page_content}"
            )

        return "\n\n".join(serialized_docs)

    async def ainvoke(self, question: str) -> OutputSchema:
        response = await self.agent.ainvoke(
            {"messages": [HumanMessage(content=question)]}
        )

        return response["structured_response"]


agent = RAGAgent(
    model=ChatGoogleGenerativeAI(
        model="gemini-flash-latest", api_key=settings.GEMINI_API_KEY
    )
)


def get_agent():
    return agent


AgentDep = Annotated[RAGAgent, Depends(get_agent)]
