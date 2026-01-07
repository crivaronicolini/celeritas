from langchain_core.documents import Document
from pathlib import Path

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pymupdf4llm import PyMuPDF4LLMLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


class VectorStore:
    def __init__(self, embeddings=None, store=None) -> None:
        self.embeddings = embeddings or OpenAIEmbeddings(
            model="text-embedding-3-large", api_key=settings.OPENAI_API_KEY
        )

        self.store: Chroma = store or Chroma(
            collection_name="collection",
            embedding_function=self.embeddings,
            persist_directory=settings.VECTOR_DB_PATH,
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            add_start_index=True,
        )

    @staticmethod
    async def aload_pdf(file_path: Path):
        loader = PyMuPDF4LLMLoader(
            file_path,
            mode="single",
            table_strategy="lines",
        )
        return await loader.aload()

    @property
    def is_empty(self) -> bool:
        if self.store.get()["ids"]:
            return False
        return True

    async def process_pdf(self, file_path: Path) -> None:
        docs: list[Document] = await self.aload_pdf(file_path)
        all_splits: list[Document] = self.text_splitter.split_documents(docs)
        await self.store.aadd_documents(documents=all_splits)

    def similarity_search(self, *args, **kwargs) -> list[Document]:
        return self.store.similarity_search(*args, **kwargs)

    def delete_all_docs(self) -> None:
        self.store.delete_collection()


vector_store = VectorStore(
    embeddings=GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001", api_key=settings.GEMINI_API_KEY
    )
)
