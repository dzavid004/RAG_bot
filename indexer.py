import os
import chromadb
from dotenv import load_dotenv

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext, Settings
# Используем OpenRouter вместо OpenAI
from llama_index.llms.openrouter import OpenRouter 
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

load_dotenv(override=True)

# Конфиги
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b:free")
# Убедись, что в .env здесь просто text-embedding-3-small
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "auto_docs")
DOCUMENTS_PATH = os.getenv("DOCUMENTS_PATH", "./documents")

# Настройки для OpenRouter
common_headers = {
    "HTTP-Referer": "https://github.com/rahim-backend",
    "X-Title": "Indexing Script"
}

# Исправляем LLM
Settings.llm = OpenRouter(
    model=LLM_MODEL,
    api_key=OPENROUTER_API_KEY,
    system_prompt=SYSTEM_PROMPT,
    default_headers=common_headers
)

# Исправляем Эмбеддинги
Settings.embed_model = OpenAIEmbedding(
    model=EMBEDDING_MODEL,
    api_key=OPENROUTER_API_KEY,
    api_base="https://openrouter.ai/api/v1",
    default_headers=common_headers
)


def index_documents():
    if not os.path.exists(DOCUMENTS_PATH):
        print(f"Ошибка: Папка {DOCUMENTS_PATH} не найдена!")
        return

    print(f"Читаю документы из папки: {DOCUMENTS_PATH}")
    documents = SimpleDirectoryReader(DOCUMENTS_PATH).load_data()
    print(f"Найдено и загружено страниц/документов: {len(documents)}")

    db = chromadb.PersistentClient(path=CHROMA_PATH)

    collections = db.list_collections()
    collection_names = [c.name for c in collections]
    
    if CHROMA_COLLECTION in collection_names:
        print(f"Коллекция '{CHROMA_COLLECTION}' уже существует — удаляю и пересоздаю")
        db.delete_collection(CHROMA_COLLECTION)

    collection = db.create_collection(CHROMA_COLLECTION)

    vector_store = ChromaVectorStore(chroma_collection=collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    print("Индексирую документы, подождите...")
    VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True
    )

    print(f"Готово. Векторная база сохранена в: {CHROMA_PATH}")


if __name__ == "__main__":
    index_documents()