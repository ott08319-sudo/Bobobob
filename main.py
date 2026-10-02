import asyncio
import logging
import os
import random
import time
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
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

# ---------- Данные ----------
games_active = {}      # {chat_id: {"game": "quiz", "data": {...}}}
scores = {}            # {chat_id: {user_id: score}}
duels = {}             # {chat_id: {"p1": id, "p2": id, "choice1": ..., "choice2": ...}}
quests = {}            # {user_id: {"step": 0, "hp": 100}}

QUESTIONS = [
    {"q": "Сколько планет в Солнечной системе?", "a": ["7", "8", "9"], "correct": "8"},
    {"q": "Кто написал «Войну и мир»?", "a": ["Толстой", "Достоевский", "Пушкин"], "correct": "Толстой"},
    {"q": "Какая самая длинная река в мире?", "a": ["Нил", "Амазонка", "Янцзы"], "correct": "Амазонка"},
    {"q": "Сколько цветов в радуге?", "a": ["5", "7", "9"], "correct": "7"},
    {"q": "Какой газ преобладает в атмосфере Земли?", "a": ["Кислород", "Азот", "Углекислый газ"], "correct": "Азот"},
    {"q": "Кто нарисовал «Мону Лизу»?", "a": ["Ван Гог", "Пикассо", "Леонардо да Винчи"], "correct": "Леонардо да Винчи"},
    {"q": "В каком году человек впервые полетел в космос?", "a": ["1957", "1961", "1969"], "correct": "1961"},
    {"q": "Сколько сторон у куба?", "a": ["4", "6", "8"], "correct": "6"},
]

FACTS = [
    "🐙 У осьминога три сердца.",
    "🍯 Мёд не портится тысячи лет.",
    "🌕 На Луне есть следы, которым миллионы лет.",
    "🦈 Акулы старше деревьев.",
    "🐌 Улитка может спать три года.",
    "🍌 Банан — это ягода, а малина — нет.",
    "⚡ Молния в 5 раз горячее поверхности Солнца.",
    "🐧 Пингвины делают предложение камешком.",
]

JOKES = [
    "— Как дела?\n— Как в сказке: чем дальше, тем страшнее.",
    "— Почему программисты путают Хэллоуин и Рождество?\n— Потому что OCT 31 == DEC 25.",
    "— Врач, я постоянно думаю, что я бот.\n— Не волнуйтесь, это просто баг.",
    "— Что сказал один байт другому?\n— Ты мне не пара.",
    "— Почему скелеты не дерутся?\n— У них нет духа.",
]

COMPLIMENTS = [
    "Ты сегодня просто огонь! 🔥",
    "С тобой этот чат стал в 100 раз лучше! ✨",
    "Ты — причина, по которой тут улыбаются! 😊",
    "У тебя отличное чувство юмора! 😄",
    "Ты умнее, чем 99% людей в этом чате! 🧠",
]

ROULETTE = ["🔴 Красное", "⚫ Чёрное", "🟢 Зеро"]
COIN = ["🪙 Орёл", "🪙 Решка"]
DICE = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]

BOT_USERNAME = None


class GameState(StatesGroup):
    quiz_waiting = State()
    duel_waiting = State()
    word_game = State()
    quest = State()
    guess_number = State()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def get_score(chat_id: int, user_id: int) -> int:
    return scores.get(chat_id, {}).get(user_id, 0)


def add_score(chat_id: int, user_id: int, points: int = 1):
    scores.setdefault(chat_id, {})
    scores[chat_id][user_id] = scores[chat_id].get(user_id, 0) + points


# ---------- Главное меню ----------
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎮 Игры", callback_data="menu_games"),
            InlineKeyboardButton(text="📊 Топ", callback_data="menu_top"),
        ],
        [
            InlineKeyboardButton(text="🎲 Рандом", callback_data="menu_random"),
            InlineKeyboardButton(text="🧠 Факт", callback_data="menu_fact"),
        ],
        [
            InlineKeyboardButton(text="😄 Шутка", callback_data="menu_joke"),
            InlineKeyboardButton(text="💬 Комплимент", callback_data="menu_compliment"),
        ],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help")],
    ])


def games_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧠 Викторина", callback_data="game_quiz")],
        [InlineKeyboardButton(text="⚔️ Дуэль", callback_data="game_duel")],
        [InlineKeyboardButton(text="🎯 Угадай число", callback_data="game_guess")],
        [InlineKeyboardButton(text="📝 Слова", callback_data="game_word")],
        [InlineKeyboardButton(text="🚀 Квест", callback_data="game_quest")],
        [InlineKeyboardButton(text="🎰 Рулетка", callback_data="game_roulette")],
        [InlineKeyboardButton(text="🪙 Монетка", callback_data="game_coin")],
        [InlineKeyboardButton(text="🎲 Кубик", callback_data="game_dice")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_main")],
    ])


# ---------- Команды ----------
@dp.message(Command("start"))
async def cmd_start(message: Message):
    name = message.from_user.first_name
    await message.answer(
        f"👋 Привет, {name}!\n\n"
        "🎉 Я развлекательный бот. Вот что я умею:\n\n"
        "🎮 /games — игры\n"
        "📊 /top — топ игроков\n"
        "🎲 /random — случайное число\n"
        "🧠 /fact — интересный факт\n"
        "😄 /joke — шутка\n"
        "💬 /compliment — комплимент\n"
        "❓ /help — помощь\n\n"
        "Также можно писать @Popagovnopopabot в любом чате!",
        reply_markup=main_menu(),
    )


@dp.message(Command("games"))
async def cmd_games(message: Message):
    await message.answer("🎮 <b>Выбери игру:</b>", reply_markup=games_menu(), parse_mode="HTML")


@dp.message(Command("top"))
async def cmd_top(message: Message):
    chat_scores = scores.get(message.chat.id, {})
    if not chat_scores:
        await message.answer("📊 Пока никто не играл!")
        return
    sorted_scores = sorted(chat_scores.items(), key=lambda x: x[1], reverse=True)[:10]
    text = "🏆 <b>Топ игроков:</b>\n\n"
    for i, (uid, sc) in enumerate(sorted_scores, 1):
        try:
            member = await bot.get_chat_member(message.chat.id, uid)
            name = member.user.first_name
        except Exception:
            name = f"Игрок {uid}"
        medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{sc}</b>\n"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("random"))
async def cmd_random(message: Message):
    await message.answer(f"🎲 Случайное число: <b>{random.randint(1, 100)}</b>", parse_mode="HTML")


@dp.message(Command("fact"))
async def cmd_fact(message: Message):
    await message.answer(f"🧠 {random.choice(FACTS)}")


@dp.message(Command("joke"))
async def cmd_joke(message: Message):
    await message.answer(f"😄 {random.choice(JOKES)}")


@dp.message(Command("compliment"))
async def cmd_compliment(message: Message):
    await message.answer(f"💬 {random.choice(COMPLIMENTS)}")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "❓ <b>Помощь</b>\n\n"
        "🎮 /games — список игр\n"
        "📊 /top — топ игроков\n"
        "🎲 /random — случайное число\n"
        "🧠 /fact — факт\n"
        "😄 /joke — шутка\n"
        "💬 /compliment — комплимент\n\n"
        "🎯 <b>Команды в группе:</b>\n"
        "• /quiz — викторина\n"
        "• /duel @юзер — дуэль\n"
        "• /guess — угадай число\n"
        "• /roulette — рулетка\n"
        "• /coin — монетка\n"
        "• /dice — кубик\n\n"
        "🔍 В любом чате: @Popagovnopopabot",
        parse_mode="HTML",
    )


# ---------- Игры ----------
@dp.message(Command("quiz"))
async def cmd_quiz(message: Message, state: FSMContext):
    q = random.choice(QUESTIONS)
    games_active[message.chat.id] = {"game": "quiz", "correct": q["correct"], "q": q["q"]}
    buttons = [[InlineKeyboardButton(text=a, callback_data=f"quiz_{a}")] for a in q["a"]]
    buttons.append([InlineKeyboardButton(text="❌ Стоп", callback_data="quiz_stop")])
    await message.answer(f"🧠 <b>Викторина!</b>\n\n{q['q']}",
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                         parse_mode="HTML")


@dp.callback_query(F.data.startswith("quiz_"))
async def cb_quiz(call: CallbackQuery):
    if call.data == "quiz_stop":
        games_active.pop(call.message.chat.id, None)
        await call.message.edit_text("🛑 Викторина остановлена.")
        await call.answer()
        return
    answer = call.data.replace("quiz_", "")
    game = games_active.get(call.message.chat.id)
    if not game or game["game"] != "quiz":
        await call.answer("Игра уже закончилась", show_alert=True)
        return
    if answer == game["correct"]:
        add_score(call.message.chat.id, call.from_user.id, 1)
        await call.message.edit_text(
            f"✅ <b>Правильно!</b>\n\n{game['q']}\n\nОтвет: <b>{game['correct']}</b>\n\n"
            f"🏆 {call.from_user.first_name} получает +1 очко!",
            parse_mode="HTML",
        )
        games_active.pop(call.message.chat.id, None)
    else:
        await call.answer(f"❌ Неверно! Попробуй ещё.", show_alert=True)


@dp.message(Command("duel"))
async def cmd_duel(message: Message, state: FSMContext):
    if not message.reply_to_message:
        await message.answer("⚔️ Ответь на сообщение того, с кем хочешь дуэль: /duel (в ответ)")
        return
    p1 = message.from_user.id
    p2 = message.reply_to_message.from_user.id
    if p1 == p2:
        await message.answer("🤦 Нельзя дуэль с самим собой!")
        return
    duels[message.chat.id] = {"p1": p1, "p2": p2}
    buttons = [
        [InlineKeyboardButton(text="✊ Камень", callback_data="duel_rock")],
        [InlineKeyboardButton(text="✋ Бумага", callback_data="duel_paper")],
        [InlineKeyboardButton(text="✌️ Ножницы", callback_data="duel_scissors")],
    ]
    await message.answer(
        f"⚔️ <b>Дуэль!</b>\n\n"
        f"{message.from_user.first_name} vs {message.reply_to_message.from_user.first_name}\n\n"
        f"Оба игрока делают выбор:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )


@dp.callback_query(F.data.startswith("duel_"))
async def cb_duel(call: CallbackQuery):
    game = duels.get(call.message.chat.id)
    if not game:
        await call.answer("Дуэль уже закончилась")
        return
    uid = call.from_user.id
    if uid not in (game["p1"], game["p2"]):
        await call.answer("Ты не участник дуэли!")
        return
    choice = call.data.replace("duel_", "")
    game[uid] = choice

    # Проверяем, сделали ли оба ход
    if all(k in game for k in (game["p1"], game["p2"])):
        c1 = game[game["p1"]]
        c2 = game[game["p2"]]
        beats = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
        names = {"rock": "✊", "paper": "✋", "scissors": "✌️"}
        try:
            m1 = await bot.get_chat_member(call.message.chat.id, game["p1"])
            m2 = await bot.get_chat_member(call.message.chat.id, game["p2"])
            n1, n2 = m1.user.first_name, m2.user.first_name
        except Exception:
            n1, n2 = "Игрок 1", "Игрок 2"

        if c1 == c2:
            result = f"🤝 <b>Ничья!</b>\n\n{n1}: {names[c1]}\n{n2}: {names[c2]}"
        elif beats[c1] == c2:
            add_score(call.message.chat.id, game["p1"], 2)
            result = f"🏆 <b>{n1} побеждает!</b>\n\n{n1}: {names[c1]}\n{n2}: {names[c2]}"
        else:
            add_score(call.message.chat.id, game["p2"], 2)
            result = f"🏆 <b>{n2} побеждает!</b>\n\n{n1}: {names[c1]}\n{n2}: {names[c2]}"

        duels.pop(call.message.chat.id, None)
        await call.message.edit_text(result, parse_mode="HTML")
    else:
        await call.answer("Ход принят! Ждём противника...", show_alert=False)


@dp.message(Command("guess"))
async def cmd_guess(message: Message, state: FSMContext):
    number = random.randint(1, 100)
    games_active[message.chat.id] = {"game": "guess", "number": number, "tries": 0}
    await message.answer("🎯 <b>Угадай число!</b>\n\nЯ загадал число от 1 до 100. Пиши свой вариант!")


@dp.message(F.text.regexp(r"^\d+$"))
async def on_number(message: Message):
    game = games_active.get(message.chat.id)
    if not game or game.get("game") != "guess":
        return
    guess = int(message.text)
    game["tries"] += 1
    if guess == game["number"]:
        add_score(message.chat.id, message.from_user.id, 3)
        await message.reply(
            f"🎉 <b>Угадал!</b>\n\nЧисло: <b>{game['number']}</b>\nПопыток: {game['tries']}\n+3 очка!",
            parse_mode="HTML",
        )
        games_active.pop(message.chat.id, None)
    elif guess < game["number"]:
        await message.reply("📈 Больше!")
    else:
        await message.reply("📉 Меньше!")


@dp.message(Command("roulette"))
async def cmd_roulette(message: Message):
    result = random.choice(ROULETTE)
    await message.answer(f"🎰 Крутим...\n\n<b>{result}</b>", parse_mode="HTML")


@dp.message(Command("coin"))
async def cmd_coin(message: Message):
    await message.answer(f"🪙 {random.choice(COIN)}")


@dp.message(Command("dice"))
async def cmd_dice(message: Message):
    await message.answer(f"🎲 {random.choice(DICE)}")


@dp.message(Command("word"))
async def cmd_word(message: Message):
    words = ["кот", "дом", "лес", "мир", "сон", "луна", "звезда", "море", "ветер", "огонь"]
    word = random.choice(words)
    games_active[message.chat.id] = {"game": "word", "word": word}
    scrambled = "".join(random.sample(word, len(word)))
    await message.answer(f"📝 <b>Угадай слово!</b>\n\nПеремешанные буквы: <code>{scrambled}</code>",
                         parse_mode="HTML")


@dp.message(F.text)
async def on_word_guess(message: Message):
    game = games_active.get(message.chat.id)
    if not game or game.get("game") != "word":
        return
    if message.text.lower().strip() == game["word"]:
        add_score(message.chat.id, message.from_user.id, 2)
        await message.reply(f"✅ <b>Правильно!</b> Слово: <b>{game['word']}</b> (+2 очка)",
                            parse_mode="HTML")
        games_active.pop(message.chat.id, None)


# ---------- Кнопки меню ----------
@dp.callback_query(F.data == "menu_main")
async def cb_main(call: CallbackQuery):
    await call.message.edit_text("🎮 Главное меню:", reply_markup=main_menu())
    await call.answer()


@dp.callback_query(F.data == "menu_games")
async def cb_games(call: CallbackQuery):
    await call.message.edit_text("🎮 <b>Выбери игру:</b>", reply_markup=games_menu(), parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "menu_top")
async def cb_top(call: CallbackQuery):
    chat_scores = scores.get(call.message.chat.id, {})
    if not chat_scores:
        await call.message.answer("📊 Пока никто не играл!")
        await call.answer()
        return
    sorted_scores = sorted(chat_scores.items(), key=lambda x: x[1], reverse=True)[:10]
    text = "🏆 <b>Топ игроков:</b>\n\n"
    for i, (uid, sc) in enumerate(sorted_scores, 1):
        try:
            member = await bot.get_chat_member(call.message.chat.id, uid)
            name = member.user.first_name
        except Exception:
            name = f"Игрок {uid}"
        medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"{i}."
        text += f"{medal} {name} — <b>{sc}</b>\n"
    await call.message.answer(text, parse_mode="HTML")
    await call.answer()


@dp.callback_query(F.data == "menu_random")
async def cb_random(call: CallbackQuery):
    await call.message.answer(f"🎲 {random.randint(1, 100)}")
    await call.answer()


@dp.callback_query(F.data == "menu_fact")
async def cb_fact(call: CallbackQuery):
    await call.message.answer(f"🧠 {random.choice(FACTS)}")
    await call.answer()


@dp.callback_query(F.data == "menu_joke")
async def cb_joke(call: CallbackQuery):
    await call.message.answer(f"😄 {random.choice(JOKES)}")
    await call.answer()


@dp.callback_query(F.data == "menu_compliment")
async def cb_compliment(call: CallbackQuery):
    await call.message.answer(f"💬 {random.choice(COMPLIMENTS)}")
    await call.answer()


@dp.callback_query(F.data == "menu_help")
async def cb_help(call: CallbackQuery):
    await call.message.answer(
        "❓ <b>Помощь</b>\n\n"
        "Игры в группе:\n"
        "• /quiz — викторина\n"
        "• /duel — дуэль (ответом на сообщение)\n"
        "• /guess — угадай число\n"
        "• /word — угадай слово\n"
        "• /roulette, /coin, /dice — рандом\n\n"
        "🔍 В любом чате: @Popagovnopopabot",
        parse_mode="HTML",
    )
    await call.answer()


# ---------- Инлайн-режим ----------
@dp.inline_query()
async def inline_handler(query: InlineQuery):
    text = query.query.strip().lower()
    results = []

    if not text:
        results = [
            InlineQueryResultArticle(
                id="rand",
                title="🎲 Случайное число",
                description="От 1 до 100",
                input_message_content=InputTextMessageContent(
                    message_text=f"🎲 Случайное число: {random.randint(1, 100)}"
                ),
            ),
            InlineQueryResultArticle(
                id="fact",
                title="🧠 Интересный факт",
                input_message_content=InputTextMessageContent(message_text=random.choice(FACTS)),
            ),
            InlineQueryResultArticle(
                id="joke",
                title="😄 Шутка",
                input_message_content=InputTextMessageContent(message_text=random.choice(JOKES)),
            ),
            InlineQueryResultArticle(
                id="compl",
                title="💬 Комплимент",
                input_message_content=InputTextMessageContent(message_text=random.choice(COMPLIMENTS)),
            ),
        ]
    elif "факт" in text or "fact" in text:
        results = [InlineQueryResultArticle(
            id="fact",
            title="🧠 Факт",
            input_message_content=InputTextMessageContent(message_text=random.choice(FACTS)),
        )]
    elif "шутк" in text or "joke" in text:
        results = [InlineQueryResultArticle(
            id="joke",
            title="😄 Шутка",
            input_message_content=InputTextMessageContent(message_text=random.choice(JOKES)),
        )]
    elif "комплимент" in text:
        results = [InlineQueryResultArticle(
            id="compl",
            title="💬 Комплимент",
            input_message_content=InputTextMessageContent(message_text=random.choice(COMPLIMENTS)),
        )]
    elif "монет" in text or "coin" in text:
        results = [InlineQueryResultArticle(
            id="coin",
            title="🪙 Монетка",
            input_message_content=InputTextMessageContent(message_text=random.choice(COIN)),
        )]
    elif "кубик" in text or "dice" in text:
        results = [InlineQueryResultArticle(
            id="dice",
            title="🎲 Кубик",
            input_message_content=InputTextMessageContent(message_text=random.choice(DICE)),
        )]
    else:
        results = [InlineQueryResultArticle(
            id="custom",
            title=f"Отправить: {query.query}",
            input_message_content=InputTextMessageContent(message_text=query.query),
        )]

    await query.answer(results=results, cache_time=0)


# ---------- Запуск ----------
async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Меню"),
        BotCommand(command="games", description="Игры"),
        BotCommand(command="top", description="Топ игроков"),
        BotCommand(command="quiz", description="Викторина"),
        BotCommand(command="duel", description="Дуэль"),
        BotCommand(command="guess", description="Угадай число"),
        BotCommand(command="word", description="Угадай слово"),
        BotCommand(command="roulette", description="Рулетка"),
        BotCommand(command="coin", description="Монетка"),
        BotCommand(command="dice", description="Кубик"),
        BotCommand(command="random", description="Случайное число"),
        BotCommand(command="fact", description="Факт"),
        BotCommand(command="joke", description="Шутка"),
        BotCommand(command="compliment", description="Комплимент"),
        BotCommand(command="help", description="Помощь"),
    ])


async def main():
    global BOT_USERNAME
    me = await bot.get_me()
    BOT_USERNAME = me.username
    await set_commands()
    logging.info(f"Бот @{BOT_USERNAME} запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
