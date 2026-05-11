import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, Update
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest
from dotenv import load_dotenv

# Импортируем твою функцию из соседнего файла
from rag import ask

load_dotenv(override=True)

# Конфиги
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
MAX_INPUT_CHARS = 2001

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message) -> None:
    first_name = message.from_user.first_name
    await message.answer(
        f"Здравствуйте, {first_name}! 🌸\n\n"
        f"Вас приветствует салон красоты Maris.\n\n"
        f"Я помогу узнать:\n"
        f"💇‍♀️ Цены на стрижки и укладки\n"
        f"💅 Маникюр и педикюр\n"
        f"✨ Косметологические процедуры\n\n"
        f"Какая услуга вас интересует?"
    )

@dp.message(F.text)
async def chat(message: Message) -> None:
    user_message = message.text

    if len(user_message) > MAX_INPUT_CHARS:
        await message.answer(
            f"⚠️ Сообщение слишком длинное. Максимум — {MAX_INPUT_CHARS} символов."
        )
        return

    placeholder = await message.answer("секундочку...🔍")

    try:
        streaming_response = await ask(user_message)
        
        if not streaming_response:
            await placeholder.edit_text("Извините, не удалось получить ответ.")
            return

        full_response = ""
        last_sent_text = ""
        chunk_size = 0

        for token in streaming_response.response_gen:
            full_response += token
            chunk_size += 1

            if chunk_size >= 20:
                if full_response.strip() != last_sent_text:
                    try:
                        await placeholder.edit_text(full_response)
                        last_sent_text = full_response
                        chunk_size = 0
                    except TelegramBadRequest:
                        pass
                    await asyncio.sleep(0.1)

        if full_response.strip() != last_sent_text:
            await placeholder.edit_text(full_response)

    except Exception as e:
        print(f"Ошибка в chat: {e}")
        try:
            await placeholder.edit_text("Произошла ошибка при поиске информации.")
        except:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    webhook_full_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(webhook_full_url)
    print(f"🚀 Webhook установлен: {webhook_full_url}")
    yield
    await bot.delete_webhook()
    print("🛑 Webhook удалён.")

app = FastAPI(lifespan=lifespan)

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request) -> JSONResponse:
    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot=bot, update=update)
    return JSONResponse({"ok": True})

@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)