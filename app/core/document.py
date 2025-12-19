from pathlib import Path
from langchain_chroma import Chroma

from langchain_pymupdf4llm import PyMuPDF4LLMLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large", api_key=settings.OPENAI_API_KEY
)

vector_store = Chroma(
    collection_name="collection",
    embedding_function=embeddings,
    persist_directory=settings.VECTOR_DB_PATH,
)


def is_empty(vector_store: Chroma) -> bool:
    if vector_store.get()["ids"]:
        return False
    return True


async def process_pdf(file_path: Path):
    loader = PyMuPDF4LLMLoader(
        file_path,
        mode="single",
        table_strategy="lines",
    )

    docs = await loader.aload()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        add_start_index=True,
    )

    all_splits = text_splitter.split_documents(docs)
    await vector_store.aadd_documents(documents=all_splits)
    return
