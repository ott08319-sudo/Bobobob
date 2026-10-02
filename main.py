import asyncio
import logging
import os
import time

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ---------- Настройки в памяти ----------
settings = {
    "text": "Приятной игры! 🎮",
    "limit_per_minute": 5,
}

# Счётчик отправок: {chat_id: [timestamp, timestamp, ...]}
send_log = {}


class EditState(StatesGroup):
    waiting_for_text = State()
    waiting_for_limit = State()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Изменить текст", callback_data="edit_text")],
        [InlineKeyboardButton(text="⏱ Лимит в минуту", callback_data="edit_limit")],
        [InlineKeyboardButton(text="📊 Текущие настройки", callback_data="show_info")],
    ])


async def show_panel(target, edit=False):
    text = (
        "🎛️ <b>Админ-панель</b>\n\n"
        f"Текст: <i>{settings['text']}</i>\n"
        f"Лимит: <b>{settings['limit_per_minute']}</b> сообщений в минуту"
    )
    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=admin_kb(), parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=admin_kb(), parse_mode="HTML")


def check_limit(chat_id: int) -> bool:
    """True — можно отправлять, False — лимит исчерпан."""
    now = time.time()
    history = send_log.get(chat_id, [])
    # оставляем только последние 60 секунд
    history = [t for t in history if now - t < 60]
    if len(history) >= settings["limit_per_minute"]:
        send_log[chat_id] = history
        return False
    history.append(now)
    send_log[chat_id] = history
    return True


# ---------- Команды ----------
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("Бот работает. Управление только у администратора.")
        return
    await show_panel(message)


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await show_panel(message)


@dp.message(Command("game"))
async def cmd_game(message: Message):
    if not is_admin(message.from_user.id):
        return
    if not check_limit(message.chat.id):
        await message.reply("⚠️ Лимит сообщений в минуту исчерпан. Подожди немного.")
        return
    await message.answer(settings["text"])


# ---------- Кнопки ----------
@dp.callback_query(F.data == "edit_text")
async def cb_edit_text(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer("✏️ Отправь новый текст:")
    await state.set_state(EditState.waiting_for_text)
    await call.answer()


@dp.callback_query(F.data == "edit_limit")
async def cb_edit_limit(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer("⏱ Введи лимит сообщений в минуту (1–60):")
    await state.set_state(EditState.waiting_for_limit)
    await call.answer()


@dp.callback_query(F.data == "show_info")
async def cb_info(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer(
        f"📊 <b>Настройки</b>\n\n"
        f"Текст: {settings['text']}\n"
        f"Лимит: {settings['limit_per_minute']} / мин",
        parse_mode="HTML",
    )
    await call.answer()


# ---------- Ввод ----------
@dp.message(EditState.waiting_for_text)
async def set_text(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    settings["text"] = message.text
    await state.clear()
    await message.answer("✅ Текст обновлён")
    await show_panel(message)


@dp.message(EditState.waiting_for_limit)
async def set_limit(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.isdigit() or not (1 <= int(message.text) <= 60):
        await message.answer("⚠️ Введи число от 1 до 60")
        return
    settings["limit_per_minute"] = int(message.text)
    await state.clear()
    await message.answer("✅ Лимит обновлён")
    await show_panel(message)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
