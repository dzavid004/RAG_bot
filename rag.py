import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import chromadb
from dotenv import load_dotenv

from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.llms import ChatMessage
from llama_index.llms.openrouter import OpenRouter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

load_dotenv(override=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is not set.")

LLM_MODEL = os.getenv("LLM_MODEL", "google/gemini-3-flash-preview")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "auto_docs")

Settings.llm = OpenRouter(
    model=LLM_MODEL,
    api_key=OPENROUTER_API_KEY,
    system_prompt=SYSTEM_PROMPT,
    default_headers={
        "HTTP-Referer": "https://github.com/my-tg-bot",
        "X-Title": "Maris Salon Bot",
    }
)

Settings.embed_model = OpenAIEmbedding(
    model=EMBEDDING_MODEL,
    api_key=OPENROUTER_API_KEY,
    api_base="https://openrouter.ai/api/v1",
)

executor = ThreadPoolExecutor()
_index = None


def get_index() -> VectorStoreIndex:
    global _index
    if _index is None:
        db = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = db.get_or_create_collection(CHROMA_COLLECTION)
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        _index = VectorStoreIndex.from_vector_store(
            vector_store,
            storage_context=storage_context,
        )
    return _index


get_index()


async def ask(question: str, history: list[dict] = []) -> str:
    try:
        index = get_index()

        chat_history = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in history
        ]

        chat_engine = index.as_chat_engine(
            chat_history=chat_history,
            similarity_top_k=2,
        )

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            executor,
            lambda: chat_engine.chat(question)
        )

        return str(response)
    except Exception as e:
        print(f"Ошибка в RAG: {e}")
        return "Извините, произошла техническая ошибка при поиске ответа."