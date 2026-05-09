# логика поиска по документам (LlamaIndex)

import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import chromadb
from dotenv import load_dotenv

from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.vector_stores.chroma import ChromaVectorStore

load_dotenv(override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "auto_docs")

Settings.llm = GoogleGenAI(
    model=GEMINI_MODEL,
    api_key=GEMINI_API_KEY,
    system_prompt=SYSTEM_PROMPT,
)

Settings.embed_model = GoogleGenAIEmbedding(
    model_name="gemini-embedding-001",
    api_key=GEMINI_API_KEY,
)

executor = ThreadPoolExecutor()


def _get_index() -> VectorStoreIndex:
    db = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = db.get_collection(CHROMA_COLLECTION)
    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(
        vector_store,
        storage_context=storage_context,
    )


async def ask(question: str) -> str:
    try:
        index = _get_index()
        query_engine = index.as_query_engine(similarity_top_k=3)

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            executor,
            lambda: query_engine.query(question)
        )
        return str(response)
    except Exception as e:
        return f"Ошибка при поиске по документам: {e}"