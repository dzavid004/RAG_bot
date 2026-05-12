import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, Update, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from dotenv import load_dotenv

from rag import ask

load_dotenv(override=True)

TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
MAX_INPUT_CHARS = 2001

BUTTON_LABELS = {
    "haircut": "Стрижки и укладки",
    "manicure": "Маникюр и педикюр",
    "cosmetology": "Косметология",
    "makeup": "Макияж и брови",
    "epilation": "Эпиляция",
}

bot = Bot(token=TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message) -> None:
    first_name = message.from_user.first_name

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💇‍♀️ Стрижки и укладки", callback_data="haircut"),
                InlineKeyboardButton(text="💅 Маникюр и педикюр", callback_data="manicure"),
            ],
            [
                InlineKeyboardButton(text="✨ Косметология", callback_data="cosmetology"),
                InlineKeyboardButton(text="💄 Макияж и брови", callback_data="makeup"),
            ],
            [
                InlineKeyboardButton(text="🪒 Эпиляция", callback_data="epilation"),
            ],
        ]
    )

    await message.answer(
        f"Здравствуйте, {first_name}! 🌸\n\n"
        f"Вас приветствует салон красоты Maris.\n\n"
        f"Я помогу узнать:\n"
        f"💇‍♀️ Цены на стрижки и укладки\n"
        f"💅 Маникюр и педикюр\n"
        f"✨ Косметологические процедуры\n\n"
        f"Какая услуга вас интересует?",
        reply_markup=keyboard,
    )


@dp.callback_query()
async def handle_button(callback: CallbackQuery) -> None:
    question = BUTTON_LABELS.get(callback.data, callback.data)
    await callback.answer()

    placeholder = await callback.message.answer("секундочку... 🔍")

    try:
        response_text = await ask(question)
        if response_text:
            await placeholder.edit_text(str(response_text))
        else:
            await placeholder.edit_text("Извините, не удалось найти информацию.")
    except Exception as e:
        print(f"Ошибка в handle_button: {e}")
        try:
            await placeholder.edit_text("Произошла ошибка при поиске информации.")
        except:
            pass


@dp.message(F.text)
async def chat(message: Message) -> None:
    user_message = message.text

    if len(user_message) > MAX_INPUT_CHARS:
        await message.answer(
            f"⚠️ Сообщение слишком длинное. Максимум — {MAX_INPUT_CHARS} символов."
        )
        return

    placeholder = await message.answer("секундочку... 🔍")

    try:
        response_text = await ask(user_message)
        if response_text:
            await placeholder.edit_text(str(response_text))
        else:
            await placeholder.edit_text("Извините, не удалось найти информацию.")
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
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot=bot, update=update)
    except Exception as e:
        print(f"Webhook error: {e}")
    return JSONResponse({"ok": True})


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)