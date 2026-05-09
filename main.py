import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, Update
from aiogram.filters import CommandStart
from dotenv import load_dotenv

from rag import ask

load_dotenv(override=True)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")

MAX_INPUT_CHARS = 2000

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message) -> None:
    first_name = message.from_user.first_name
    await message.answer(
        f"Здравствуйте, {first_name}! Я помощник салона красоты Maris.\n"
        f"Задавайте вопросы по услугам, ценам и условиям оказания услуг."
    )


@dp.message(F.text)
async def chat(message: Message) -> None:
    user_message = message.text

    if len(user_message) > MAX_INPUT_CHARS:
        await message.answer(
            f"⚠️ Сообщение слишком длинное ({len(user_message)} символов). "
            f"Максимум — {MAX_INPUT_CHARS} символов."
        )
        return

    placeholder = await message.answer("Ищу информацию... 🔍")

    try:
        response_text = await ask(user_message)
        await placeholder.edit_text(response_text)
    except Exception as e:
        await placeholder.edit_text(f"Произошла ошибка: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    webhook_full_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook_full_url)
    print(f"Webhook установлен: {webhook_full_url}")
    yield
    await bot.delete_webhook()
    print("Webhook удалён.")


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
    uvicorn.run("main:app", host="0.0.0.0", port=port)