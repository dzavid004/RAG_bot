import os
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, Update, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from dotenv import load_dotenv

from rag import ask

load_dotenv(override=True)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
MAX_INPUT_CHARS = 2001
MAX_HISTORY = 3

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_histories: dict[int, list[dict]] = {}


def get_history(user_id: int) -> list[dict]:
    if user_id not in user_histories:
        user_histories[user_id] = []
    return user_histories[user_id]


def add_to_history(user_id: int, role: str, content: str) -> None:
    history = get_history(user_id)
    history.append({"role": role, "content": content})
    if len(history) > MAX_HISTORY:
        user_histories[user_id] = history[-MAX_HISTORY:]


def get_services_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💇‍♀️ Стрижки и укладки", callback_data="Стрижки и укладки"),
            InlineKeyboardButton(text="💅 Маникюр и педикюр", callback_data="Маникюр и педикюр"),
        ],
        [
            InlineKeyboardButton(text="✨ Косметология", callback_data="Косметология"),
            InlineKeyboardButton(text="💄 Макияж и брови", callback_data="Макияж и брови"),
        ],
        [
            InlineKeyboardButton(text="🪒 Эпиляция", callback_data="Эпиляция"),
        ],
    ])


async def process_query(user_message: str, reply_target: Message, user_id: int) -> None:
    placeholder = await reply_target.answer("секундочку...🔍")

    try:
        history = get_history(user_id)
        response_text = await ask(user_message, history)

        if response_text:
            add_to_history(user_id, "user", user_message)
            add_to_history(user_id, "assistant", response_text)
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
    user_histories[message.from_user.id] = []

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


@dp.callback_query(F.data)
async def handle_button(callback: CallbackQuery) -> None:
    await callback.answer()
    await process_query(callback.data, callback.message, callback.from_user.id)


@dp.message(F.text)
async def chat(message: Message) -> None:
    user_message = message.text

    if len(user_message) > MAX_INPUT_CHARS:
        await message.answer(
            f"⚠️ Сообщение слишком длинное. Максимум — {MAX_INPUT_CHARS} символов."
        )
        return

    await process_query(user_message, message, message.from_user.id)


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