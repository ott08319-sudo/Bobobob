import asyncio
import logging
import os
import time
import random
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
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
    "variants": ["Приятной игры! 🎮", "Удачи! 🍀", "Хорошей игры! 🏆"],
    "use_random": False,
    "limit_per_minute": 20,
    "cooldown_seconds": 5,       # пауза между сообщениями в одном чате
    "enabled": True,             # глобальный вкл/выкл
    "stats_sent": 0,             # сколько всего отправлено
    "started_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
}

send_log = {}   # {chat_id: [timestamps]}
last_sent = {}  # {chat_id: timestamp}


class EditState(StatesGroup):
    waiting_for_text = State()
    waiting_for_variants = State()
    waiting_for_limit = State()
    waiting_for_cooldown = State()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ---------- Клавиатура ----------
def admin_kb():
    status = "🟢 Вкл" if settings["enabled"] else "🔴 Выкл"
    rand = "🎲 Вкл" if settings["use_random"] else "📝 Выкл"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Изменить текст", callback_data="edit_text")],
        [InlineKeyboardButton(text="🎲 Варианты фраз", callback_data="edit_variants")],
        [InlineKeyboardButton(text=f"🎲 Рандом: {rand}", callback_data="toggle_random")],
        [InlineKeyboardButton(text="⏱ Лимит в минуту", callback_data="edit_limit")],
        [InlineKeyboardButton(text="⏸ Пауза (сек)", callback_data="edit_cooldown")],
        [InlineKeyboardButton(text=f"{status} бота", callback_data="toggle_enabled")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")],
        [InlineKeyboardButton(text="👀 Предпросмотр", callback_data="preview")],
    ])


async def show_panel(target, edit=False):
    text = (
        "🎛️ <b>Админ-панель</b>\n\n"
        f"Текст: <i>{settings['text'][:50]}</i>\n"
        f"Рандом: {'🎲 да' if settings['use_random'] else '📝 нет'}\n"
        f"Лимит: <b>{settings['limit_per_minute']}</b>/мин\n"
        f"Пауза: <b>{settings['cooldown_seconds']}</b> сек\n"
        f"Статус: {'🟢 включён' if settings['enabled'] else '🔴 выключен'}"
    )
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=admin_kb(), parse_mode="HTML")
        except Exception:
            await target.message.answer(text, reply_markup=admin_kb(), parse_mode="HTML")
    else:
        await target.answer(text, reply_markup=admin_kb(), parse_mode="HTML")


# ---------- Хелперы ----------
def pick_text() -> str:
    if settings["use_random"] and settings["variants"]:
        return random.choice(settings["variants"])
    return settings["text"]


def check_limit(chat_id: int) -> bool:
    now = time.time()
    history = send_log.get(chat_id, [])
    history = [t for t in history if now - t < 60]
    if len(history) >= settings["limit_per_minute"]:
        send_log[chat_id] = history
        return False
    history.append(now)
    send_log[chat_id] = history
    return True


def check_cooldown(chat_id: int) -> bool:
    now = time.time()
    last = last_sent.get(chat_id, 0)
    if now - last < settings["cooldown_seconds"]:
        return False
    last_sent[chat_id] = now
    return True


def can_send(chat_id: int) -> bool:
    if not settings["enabled"]:
        return False
    if not check_limit(chat_id):
        return False
    if not check_cooldown(chat_id):
        return False
    return True


# ========== ИНЛАЙН-РЕЖИМ ==========
@dp.inline_query()
async def inline_handler(query: InlineQuery):
    if not settings["enabled"]:
        await query.answer(results=[], cache_time=0,
                           switch_pm_text="Бот выключен", switch_pm_parameter="off")
        return

    results = []
    phrases = settings["variants"] if settings["use_random"] and settings["variants"] else [settings["text"]]
    for i, phrase in enumerate(phrases[:10]):
        results.append(
            InlineQueryResultArticle(
                id=str(i),
                title=phrase[:50],
                description="Нажми, чтобы отправить",
                input_message_content=InputTextMessageContent(message_text=phrase),
            )
        )
    await query.answer(results=results, cache_time=0)


# ========== Команды ==========
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


# ========== Кнопки ==========
@dp.callback_query(F.data == "edit_text")
async def cb_edit_text(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer("✏️ Отправь новый основной текст:")
    await state.set_state(EditState.waiting_for_text)
    await call.answer()


@dp.callback_query(F.data == "edit_variants")
async def cb_edit_variants(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer(
        "🎲 Отправь варианты фраз, каждый с новой строки:\n\n"
        "Пример:\nПриятной игры! 🎮\nУдачи! 🍀\nХорошей игры! 🏆"
    )
    await state.set_state(EditState.waiting_for_variants)
    await call.answer()


@dp.callback_query(F.data == "toggle_random")
async def cb_toggle_random(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    settings["use_random"] = not settings["use_random"]
    await show_panel(call)
    await call.answer("Обновлено")


@dp.callback_query(F.data == "edit_limit")
async def cb_edit_limit(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer("⏱ Введи лимит сообщений в минуту (1–60):")
    await state.set_state(EditState.waiting_for_limit)
    await call.answer()


@dp.callback_query(F.data == "edit_cooldown")
async def cb_edit_cooldown(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer("⏸ Введи паузу между сообщениями в секундах (0–300):")
    await state.set_state(EditState.waiting_for_cooldown)
    await call.answer()


@dp.callback_query(F.data == "toggle_enabled")
async def cb_toggle_enabled(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    settings["enabled"] = not settings["enabled"]
    await show_panel(call)
    await call.answer("Обновлено")


@dp.callback_query(F.data == "show_stats")
async def cb_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"Отправлено всего: <b>{settings['stats_sent']}</b>\n"
        f"Запущен: {settings['started_at']}\n"
        f"Вариантов фраз: {len(settings['variants'])}\n"
        f"Рандом: {'вкл' if settings['use_random'] else 'выкл'}\n"
        f"Лимит: {settings['limit_per_minute']}/мин\n"
        f"Пауза: {settings['cooldown_seconds']} сек",
        parse_mode="HTML",
    )
    await call.answer()


@dp.callback_query(F.data == "preview")
async def cb_preview(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.message.answer(f"👀 Предпросмотр:\n\n{pick_text()}")
    await call.answer()


# ========== Ввод ==========
@dp.message(EditState.waiting_for_text)
async def set_text(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    settings["text"] = message.text
    await state.clear()
    await message.answer("✅ Текст обновлён")
    await show_panel(message)


@dp.message(EditState.waiting_for_variants)
async def set_variants(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    lines = [line.strip() for line in message.text.split("\n") if line.strip()]
    if not lines:
        await message.answer("⚠️ Пришли хотя бы одну фразу")
        return
    settings["variants"] = lines
    settings["use_random"] = True
    await state.clear()
    await message.answer(f"✅ Сохранено {len(lines)} вариантов. Рандом включён.")
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


@dp.message(EditState.waiting_for_cooldown)
async def set_cooldown(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if not message.text.isdigit() or not (0 <= int(message.text) <= 300):
        await message.answer("⚠️ Введи число от 0 до 300")
        return
    settings["cooldown_seconds"] = int(message.text)
    await state.clear()
    await message.answer("✅ Пауза обновлена")
    await show_panel(message)


# ========== Запуск ==========
async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Админ-панель"),
        BotCommand(command="admin", description="Открыть панель"),
    ])


async def main():
    await set_commands()
    logging.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
