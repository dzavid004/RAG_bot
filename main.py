import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, Update, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest
from dotenv import load_dotenv

from rag import ask

load_dotenv(override=True)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
MAX_INPUT_CHARS = 2001

bot = Bot(token=TOKEN)
dp = Dispatcher()


def get_services_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="💇‍♀️ Стрижки и укладки"),
                KeyboardButton(text="💅 Маникюр и педикюр"),
            ],
            [
                KeyboardButton(text="✨ Косметология"),
                KeyboardButton(text="💄 Макияж и брови"),
            ],
            [
                KeyboardButton(text="🪒 Эпиляция"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Или напишите свой вопрос...",
    )


async def process_query(user_message: str, reply_target: Message) -> None:
    placeholder = await reply_target.answer("секундочку...🔍")

    try:
        response_text = await ask(user_message)

        if response_text:
            await placeholder.edit_text(str(response_text))
        else:
            await placeholder.edit_text("Извините, не удалось найти информацию.")

    except Exception as e:
        print(f"Ошибка в process_query: {e}")
        try:
            await placeholder.edit_text("Произошла ошибка при поиске информации.")
        except Exception:
            pass


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
        f"Какая услуга вас интересует?",
        reply_markup=get_services_keyboard(),
    )


@dp.message(F.text)
async def chat(message: Message) -> None:
    user_message = message.text

    if len(user_message) > MAX_INPUT_CHARS:
        await message.answer(
            f"⚠️ Сообщение слишком длинное. Максимум — {MAX_INPUT_CHARS} символов."
        )
        return

    await process_query(user_message, message)


@asynccontextmanager
async def lifespan(app: FastAPI):
    webhook_full_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(
        webhook_full_url,
        allowed_updates=["message", "callback_query"]
    )
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