# скрипт индексации документов (запускается 1 раз)
import os
import chromadb
from dotenv import load_dotenv

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, Settings
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.vector_stores.chroma import ChromaVectorStore

load_dotenv(override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "auto_docs")
DOCUMENTS_PATH = os.getenv("DOCUMENTS_PATH", "./documents")

Settings.llm = GoogleGenAI(
    model=GEMINI_MODEL,
    api_key=GEMINI_API_KEY,
    system_prompt=SYSTEM_PROMPT,
)

Settings.embed_model = GoogleGenAIEmbedding(
    model_name="gemini-embedding-001",
    api_key=GEMINI_API_KEY,
)


def index_documents():
    print(f"Читаю документы из папки: {DOCUMENTS_PATH}")

    documents = SimpleDirectoryReader(DOCUMENTS_PATH).load_data()
    print(f"Найдено и загружено страниц/документов: {len(documents)}")

    db = chromadb.PersistentClient(path=CHROMA_PATH)

    existing_collections = [c.name for c in db.list_collections()]
    if CHROMA_COLLECTION in existing_collections:
        print(f"Коллекция '{CHROMA_COLLECTION}' уже существует — удаляю и пересоздаю")
        db.delete_collection(CHROMA_COLLECTION)

    collection = db.create_collection(CHROMA_COLLECTION)

    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    print("Индексирую документы, подождите...")
    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
    )

    print(f"Готово. Векторная база сохранена в: {CHROMA_PATH}")


if __name__ == "__main__":
    index_documents()